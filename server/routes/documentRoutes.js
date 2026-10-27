import express from "express";
import upload from "../middleware/uploadMiddleware.js";
import {
  uploadDocument,
  getDocumentCount,
  getDocumentCountWithType,
  getDocuments, 
  semanticSearchDocuments,
  askDocumentQuestion,
} from "../controllers/documentController.js";
import protect from "../middleware/authMiddleware.js";

const router = express.Router();

router.post("/upload", protect, upload.array("document", 50), uploadDocument);

router.get("/count", protect, getDocumentCount);
router.get("/countType", protect, getDocumentCountWithType);

router.get("/search", protect, semanticSearchDocuments);
router.post("/ask", protect, askDocumentQuestion);

router.get("/", protect, getDocuments);

export default router;
