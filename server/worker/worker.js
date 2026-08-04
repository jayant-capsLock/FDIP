import {
  getNextPendingJob,
  markProcessing,
  markCompleted,
  markFailed,
} from "../services/jobService.js";

const processNextJob = async () => {
  const job = await getNextPendingJob();
  if (!job) {
    console.log("No pending jobs.");
    return;
  }

  console.log(`Found Job: ${job.id}`);

  try {
    await markProcessing(job.id);

    await new Promise((resolve) => {
      setTimeout(resolve, 3000);
    });

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
