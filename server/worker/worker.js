import {
  getNextPendingJob,
  markProcessing,
  markCompleted,
  markFailed,
} from "../services/jobService.js";

import { downloadDocument } from "../services/storageService.js";
import { extractText } from "../services/ocrService.js";
import { saveDocumentText } from "../services/textService.js";
import { chunkDocument } from "../services/chunkingService.js";
import embeddingService from "../services/embeddingService.js";
import qdrantService from "../services/qdrantService.js";

const processNextJob = async () => {
  const job = await getNextPendingJob();
  if (!job) {
    console.log("No pending jobs.");
    return;
  }

  console.log(`Found Job: ${job.id}`);

  try {
    await markProcessing(job.id);

    const buffer = await downloadDocument(job.storage_path);

    const extractedInfo = await extractText(
      buffer,
      job.original_filename,
      job.mime_type,
    );

    const extractedText = extractedInfo.text;
    const extractedType = extractedInfo.document_type;
    const extractedConfidence = extractedInfo.confidence;
    const extractedMetadata = extractedInfo.metadata;
    const chunks = chunkDocument(extractedText);

    const embeddings = await embeddingService.generateEmbeddings(
      chunks.map((chunk) => chunk.chunk_text),
    );

    console.log(`Generated ${embeddings.length} embeddings.`);

    const { savedChunks } = await saveDocumentText(
      job.document_id,
      1,
      extractedText,
      extractedType,
      extractedConfidence,
      extractedMetadata,
      chunks,
      embeddings,
    );

    await qdrantService.upsertChunks(savedChunks, embeddings);

    await markCompleted(job.id);

    console.log(`Completed Job: ${job.id}`);
  } catch (error) {
    await markFailed(job.id, error.message);
    console.error(`Failed Job: ${job.id}`);
    console.error(error.message);
  }
};

console.log("Worker started...");

const workerLoop = async () => {
  while (true) {
    await processNextJob();

    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
};

console.log("Worker started...");

workerLoop();
