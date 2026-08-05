import {
  getNextPendingJob,
  markProcessing,
  markCompleted,
  markFailed,
} from "../services/jobService.js";

import { downloadDocument } from "../services/storageService.js";
import { extractText } from "../services/ocrService.js";
import { saveDocumentText } from "../services/textService.js";

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

    const extractedText = await extractText(
      buffer,
      job.original_filename,
      job.mime_type,
    );

    await saveDocumentText(job.document_id, 1, extractedText);

    await markCompleted(job.id);

    console.log(`Completed Job: ${job.id}`);
  } catch (error) {
    await markFailed(job.id, error.message);
    console.error(`Failed Job: ${job.id}`);
    console.error(error.message);
  }
};

console.log("Worker started...");

setInterval(processNextJob, 5000);
