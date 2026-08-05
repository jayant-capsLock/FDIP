import pool from "../config/db.js";

export const saveDocumentText = async (
  documentId,
  pageNumber,
  extractedText
) => {
  const result = await pool.query(
    `
    INSERT INTO document_text
    (document_id, page_number, extracted_text)
    VALUES ($1, $2, $3)
    RETURNING *
    `,
    [documentId, pageNumber, extractedText]
  );

  return result.rows[0];
};