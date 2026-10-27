import pool from "../config/db.js";
import supabase from "../config/supabase.js";
import crypto from "crypto";
import { createJob } from "../services/jobService.js";
import retrievalService from "../services/retrievalService.js";
import ragService from "../services/ragService.js";

export const semanticSearchDocuments = async (req, res) => {
  try {
    const queryText = req.query.q?.trim();

    if (!queryText) {
      return res.status(400).json({
        success: false,
        message: "Search query is required.",
      });
    }

    // 1. Get documents belonging to the authenticated user
    const userDocuments = await pool.query(
      `
      SELECT id
      FROM public.documents
      WHERE user_id = $1
      `,
      [req.user.id]
    );

    const allowedDocumentIds = userDocuments.rows.map(
      (document) => document.id
    );

    if (allowedDocumentIds.length === 0) {
      return res.json({
        success: true,
        documents: [],
      });
    }

    // 2. Retrieve matching chunks from Qdrant
    const chunks = await retrievalService.searchChunks(
      queryText,
      50,
      null,
      allowedDocumentIds
    );

    // 3. Group chunks by document and retain the best score
    const documentScores = new Map();

    for (const chunk of chunks) {
      const existing = documentScores.get(chunk.document_id);

      if (!existing || chunk.score > existing.score) {
        documentScores.set(chunk.document_id, {
          score: chunk.score,
          bestChunk: chunk.chunk_text,
        });
      }
    }

    // 4. Rank documents by their best matching chunk
    const rankedDocuments = [...documentScores.entries()]
      .sort((a, b) => b[1].score - a[1].score)
      .slice(0, 10);

    if (rankedDocuments.length === 0) {
      return res.json({
        success: true,
        documents: [],
      });
    }

    const documentIds = rankedDocuments.map(
      ([documentId]) => documentId
    );

    // 5. Fetch document details from PostgreSQL
    const result = await pool.query(
      `
      SELECT
        d.id,
        d.filename,
        d.original_filename,
        d.storage_path,
        d.mime_type,
        d.file_size,
        dt.document_type,
        LOWER(
          COALESCE(pj.status::text, d.status)
        ) AS status,
        d.uploaded_at,
        d.processed_at,
        d.metadata

      FROM public.documents d

      LEFT JOIN public.document_text dt
        ON dt.document_id = d.id

      LEFT JOIN public.processing_jobs pj
        ON pj.document_id = d.id

      WHERE d.user_id = $1
        AND d.id = ANY($2::uuid[])
      `,
      [req.user.id, documentIds]
    );

    // 6. Attach preview URLs and similarity scores
    const documents = [];

    for (const document of result.rows) {
      const { data } = await supabase.storage
        .from("documents")
        .createSignedUrl(document.storage_path, 3600);

      const match = documentScores.get(document.id);

      documents.push({
        ...document,
        preview_url: data?.signedUrl || null,
        search_score: match.score,
        best_matching_chunk: match.bestChunk,
      });
    }

    // Preserve Qdrant relevance order
    documents.sort(
      (a, b) => b.search_score - a.search_score
    );

    res.json({
      success: true,
      documents,
    });

  } catch (err) {
    console.error("Semantic search failed:", err);

    res.status(500).json({
      success: false,
      message: "Semantic search failed.",
    });
  }
};


export const getDocuments = async (req, res) => {
  try {
      const result = await pool.query(
        `
        SELECT
          d.id,
          d.filename,
          d.original_filename,
          d.storage_path,
          d.mime_type,
          d.file_size,
          dt.document_type,

          LOWER(
            COALESCE(pj.status::text, d.status)
          ) AS status,

          d.uploaded_at,
          d.processed_at,
          d.metadata

        FROM public.documents d

        LEFT JOIN public.document_text dt
          ON dt.document_id = d.id

        LEFT JOIN public.processing_jobs pj
          ON pj.document_id = d.id

        WHERE d.user_id = $1

        ORDER BY d.uploaded_at DESC
        `,
        [req.user.id],
      );

    const documents = [];

    for (const document of result.rows) {
      const { data } = await supabase.storage
        .from("documents")
        .createSignedUrl(document.storage_path, 3600);

      documents.push({
        ...document,
        preview_url: data?.signedUrl || null,
      });
    }

    res.json({
      success: true,
      documents: documents,
    });
  } catch (err) {
    console.error(err);

    res.status(500).json({
      success: false,
      message: "Failed to fetch documents.",
    });
  }
};

export const uploadDocument = async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({
        success: false,
        message: "No files uploaded.",
      });
    }

    const uploadedDocuments = [];

    for (const file of req.files) {
      const extension = file.originalname.split(".").pop();

      const filename = `${crypto.randomUUID()}.${extension}`;

      const { data, error } = await supabase.storage
        .from("documents")
        .upload(filename, file.buffer, {
          contentType: file.mimetype,
          upsert: false,
        });

      if (error) {
        throw error;
      }

      const result = await pool.query(
        `
        INSERT INTO documents
        (
          user_id,
          filename,
          original_filename,
          storage_path,
          mime_type,
          file_size
        )
        VALUES ($1,$2,$3,$4,$5,$6)
        RETURNING *
        `,
        [
          req.user.id,
          filename,
          file.originalname,
          data.path,
          file.mimetype,
          file.size,
        ],
      );

      const document = result.rows[0];

      await createJob(document.id);

      uploadedDocuments.push(document);
    }

    res.status(201).json({
      success: true,
      message: `${uploadedDocuments.length} document(s) uploaded successfully.`,
      documents: uploadedDocuments,
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      success: false,
      message: "Upload failed.",
    });
  }
};

export const getDocumentCount = async (req, res) => {
  try {
    const result = await pool.query(
      `
      SELECT COUNT(*) AS count
      FROM documents
      WHERE user_id = $1
      `,
      [req.user.id],
    );

    res.json({
      count: Number(result.rows[0].count),
    });
  } catch (err) {
    console.error(err);

    res.status(500).json({
      message: "Failed to fetch document count.",
    });
  }
};

export const getDocumentCountWithType = async (req, res) => {
  try {
    const result = await pool.query(
      `
      SELECT
        document_text.document_type,
        COUNT(DISTINCT document_text.document_id)::int AS document_count
      FROM public.document_text
      INNER JOIN public.documents
        ON documents.id = document_text.document_id
      WHERE documents.user_id = $1
        AND document_text.document_type IS NOT NULL
      GROUP BY document_text.document_type
      ORDER BY document_count DESC, document_text.document_type;
      `,
      [req.user.id],
    );

    res.json(result.rows);
  } catch (err) {
    console.error(err);

    res.status(500).json({
      message: "Failed to fetch document count.",
    });
  }
};


export const askDocumentQuestion = async (req, res) => {
  try {
    const question = req.body.question?.trim();

    if (!question) {
      return res.status(400).json({
        success: false,
        message: "Question is required.",
      });
    }

    // Get documents belonging to the authenticated user
    const userDocuments = await pool.query(
      `
      SELECT id, original_filename
      FROM public.documents
      WHERE user_id = $1
      `,
      [req.user.id]
    );

    const allowedDocumentIds = userDocuments.rows.map(
      (document) => document.id
    );

    if (allowedDocumentIds.length === 0) {
      return res.json({
        success: true,
        answer: "You haven't uploaded any documents yet.",
        sources: [],
      });
    }

    // Retrieve relevant chunks from Qdrant
    const chunks = await retrievalService.searchChunks(
      question,
      5,
      null,
      allowedDocumentIds
    );

    if (chunks.length === 0) {
      return res.json({
        success: true,
        answer: "I couldn't find relevant information in your documents.",
        sources: [],
      });
    }

    // Map document IDs to filenames
    const documentMap = new Map(
      userDocuments.rows.map((document) => [
        document.id,
        document.original_filename,
      ])
    );

    const enrichedChunks = chunks.map((chunk) => ({
      ...chunk,
      document_name:
        documentMap.get(chunk.document_id) || "Unknown document",
    }));

    // Generate answer using the LLM
    const answer = await ragService.generateAnswer(
      question,
      enrichedChunks
    );

    // Prepare source information
    const sources = enrichedChunks.map((chunk, index) => ({
      source_number: index + 1,
      document_id: chunk.document_id,
      document_name: chunk.document_name,
      chunk_index: chunk.chunk_index,
      page_start: chunk.page_start,
      page_end: chunk.page_end,
      score: chunk.score,
    }));

    res.json({
      success: true,
      answer,
      sources,
    });

  } catch (error) {
    console.error("RAG error:", error);

    res.status(500).json({
      success: false,
      message: "Failed to generate answer.",
    });
  }
};
