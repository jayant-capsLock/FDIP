import pool from "../config/db.js";

export const createJob = async (documentId) => {
    const result = await pool.query(
        `
        INSERT INTO processing_jobs (document_id)
        VALUES ($1)
        RETURNING *
        `, [documentId]
    );

    return result.rows[0];
};

export const getNextPendingJob = async () => {
    const result = await pool.query(`
        SELECT * 
        FROM processing_jobs 
        WHERE status = 'Pending' 
        ORDER BY created_at ASC 
        LIMIT 1
        `);

    return result.rows[0];
};

export const markProcessing = async (jobId)=> {
    const result = await pool.query(
        `
        UPDATE processing_jobs
        SET status = 'Processing', 
            started_at = NOW()
        WHERE id = $1
        RETURNING *
        `
    , [jobId]);

    return result.rows[0];
}

export const markCompleted = async (jobId)=> {
    const result = await pool.query(
        `
        UPDATE processing_jobs
        SET status = 'Completed', 
            completed_at = NOW()
        WHERE id = $1
        RETURNING *
        `
    , [jobId]);

    return result.rows[0];
}

export const markFailed = async (jobId, errorMessage)=> {
    const result = await pool.query(
        `
        UPDATE processing_jobs
        SET status = 'Failed', 
            completed_at = NOW(),
            error_message = $2
        WHERE id = $1
        RETURNING *
        `
    , [jobId, errorMessage]);

    return result.rows[0];
}