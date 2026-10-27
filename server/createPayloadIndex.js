import "dotenv/config";
import qdrantClient from "./config/qdrantClient.js";

const COLLECTION_NAME = "fdip_document_chunks";

const createIndex = async () => {
  try {
    await qdrantClient.createPayloadIndex(COLLECTION_NAME, {
      field_name: "document_id",
      field_schema: "keyword",
      wait: true,
    });

    console.log("Payload index created successfully!");
  } catch (error) {
    console.error("Failed to create payload index:", error);
  }
};

createIndex();