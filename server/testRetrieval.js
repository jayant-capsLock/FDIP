
import "dotenv/config";
import retrievalService from "./services/retrievalService.js";

async function testRetrieval() {
  try {
    const results = await retrievalService.searchChunks(
      "invoice jharkhand software cloudzen",
      1
    );

    console.log("\nRelevant chunks:\n");

    results.forEach((chunk, index) => {
      console.log(`Result ${index + 1}`);
      console.log("Score:", chunk.score);
      console.log("Document ID:", chunk.document_id);
      console.log("Chunk:", chunk.chunk_text);
      console.log("---------------------------");
    });
  } catch (error) {
    console.error("Retrieval failed:");
    console.error(error.response?.data || error.message);
  }
}

testRetrieval();
