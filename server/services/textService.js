
import pool from "../config/db.js";

export const saveDocumentText = async (
  documentId,
  pageNumber,
  extractedText,
  extractedType,
  extractedConfidence,
  extractedMetadata,
  chunks,
  embeddings
) => {
  if (chunks.length !== embeddings.length) {
    throw new Error("Chunks and embeddings count mismatch");
  }

  // Save extracted OCR text
  const result = await pool.query(
    `
    INSERT INTO document_text
    (document_id, page_number, extracted_text, document_type, confidence)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING *;
    `,
    [
      documentId,
      pageNumber,
      extractedText,
      extractedType,
      extractedConfidence
    ]
  );

  // Update document metadata
  await pool.query(
    `
    UPDATE documents
    SET metadata = $1
    WHERE id = $2;
    `,
    [extractedMetadata, documentId]
  );

  // Remove previously generated chunks
  await pool.query(
    `
    DELETE FROM document_chunks
    WHERE document_id = $1;
    `,
    [documentId]
  );

  // Save chunks and collect their database IDs
  const savedChunks = [];

  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];

    const chunkResult = await pool.query(
      `
      INSERT INTO document_chunks
      (
        document_id,
        chunk_index,
        page_start,
        page_end,
        chunk_text,
        char_count,
        embedding
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING id;
      `,
      [
        documentId,
        chunk.chunk_index,
        chunk.page_start,
        chunk.page_end,
        chunk.chunk_text,
        chunk.char_count,
        JSON.stringify(embeddings[i])
      ]
    );

    savedChunks.push({
      id: chunkResult.rows[0].id,
      document_id: documentId,
      ...chunk
    });
  }

  return {
    documentText: result.rows[0],
    savedChunks
  };
};
