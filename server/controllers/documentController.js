import pool from "../config/db.js";
import supabase from "../config/supabase.js";
import crypto from "crypto";

export const uploadDocument = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: "No file uploaded.",
      });
    }

    const extension = req.file.originalname.split(".").pop();

    const filename = `${crypto.randomUUID()}.${extension}`;

    const { data, error } = await supabase.storage
      .from("documents")
      .upload(filename, req.file.buffer, {
        contentType: req.file.mimetype,
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
        req.file.originalname,
        data.path,
        req.file.mimetype,
        req.file.size,
      ],
    );

    res.status(201).json({
      success: true,
      message: "Document uploaded successfully.",
      document: result.rows[0],
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
      [req.user.id]
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
