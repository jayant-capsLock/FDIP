import pool from "../config/db.js";

export const createJob = async (documentId) => {
  const result = await pool.query(
    `
        INSERT INTO processing_jobs (document_id)
        VALUES ($1)
        RETURNING *
        `,
    [documentId],
  );

  return result.rows[0];
};

export const getNextPendingJob = async () => {
  const result = await pool.query(`
        SELECT 
            processing_jobs.id,
            processing_jobs.document_id,
            processing_jobs.status,

            documents.storage_path,
            documents.original_filename,
            documents.mime_type
        FROM processing_jobs 
        JOIN documents
            ON processing_jobs.document_id = documents.id
        WHERE processing_jobs.status = 'Pending' 
        ORDER BY processing_jobs.created_at ASC 
        LIMIT 1
        `);

  return result.rows[0];
};

export const markProcessing = async (jobId) => {
  const result = await pool.query(
    `
        UPDATE processing_jobs
        SET status = 'Processing', 
            started_at = NOW()
        WHERE id = $1
        RETURNING *
        `,
    [jobId],
  );

  return result.rows[0];
};

export const markCompleted = async (jobId) => {
  const result = await pool.query(
    `
        UPDATE processing_jobs
        SET status = 'Completed', 
            completed_at = NOW()
        WHERE id = $1
        RETURNING *
        `,
    [jobId],
  );

  return result.rows[0];
};

export const markFailed = async (jobId, errorMessage) => {
  const result = await pool.query(
    `
        UPDATE processing_jobs
        SET status = 'Failed', 
            completed_at = NOW(),
            error_message = $2
        WHERE id = $1
        RETURNING *
        `,
    [jobId, errorMessage],
  );

  return result.rows[0];
};
