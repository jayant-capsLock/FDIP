import express from "express";
import upload from "../middleware/uploadMiddleware.js";
import {
    uploadDocument,
    getDocumentCount,
} from "../controllers/documentController.js";
import protect from "../middleware/authMiddleware.js";

const router = express.Router();

router.post(
  "/upload",
  protect,
  upload.single("document"),
  uploadDocument
);

router.get("/count", protect, getDocumentCount);

export default router;