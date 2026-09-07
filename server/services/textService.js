import pool from "../config/db.js";

export const saveDocumentText = async (
  documentId,
  pageNumber,
  extractedText,
  extractedType,
  extractedConfidence,
  extractedMetadata
) => {
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

  await pool.query(
    `
    UPDATE documents
    SET metadata = $1
    WHERE id = $2;
    `,
    [
      extractedMetadata,
      documentId
    ]
  );

  return result.rows[0];
};