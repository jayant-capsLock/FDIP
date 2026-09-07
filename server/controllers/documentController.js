import pool from "../config/db.js";
import supabase from "../config/supabase.js";
import crypto from "crypto";
import { createJob } from "../services/jobService.js";

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
      WITH document_types AS (
        SELECT *
        FROM (
          VALUES
            (1, 'bank_statement'),
            (2, 'invoice'),
            (3, 'payslip'),
            (4, 'tax_document'),
            (5, 'receipt')
        ) AS t(sort_order, document_type)
      )

      SELECT
        dt.document_type,
        COUNT(DISTINCT d.document_id)::int AS document_count

      FROM document_types dt

      LEFT JOIN (
        SELECT DISTINCT
          document_text.document_id,
          document_text.document_type
        FROM public.document_text
        INNER JOIN public.documents
          ON documents.id = document_text.document_id
        WHERE documents.user_id = $1
      ) d
        ON d.document_type = dt.document_type

      GROUP BY
        dt.sort_order,
        dt.document_type

      ORDER BY
        dt.sort_order;
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
