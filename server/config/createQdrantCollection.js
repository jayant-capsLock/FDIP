import "dotenv/config";
import qdrantClient from "./qdrantClient.js";

const COLLECTION_NAME = "fdip_document_chunks";

async function createCollection() {
  try {
    const collections = await qdrantClient.getCollections();

    const exists = collections.collections.some(
      (collection) => collection.name === COLLECTION_NAME
    );

    if (exists) {
      console.log("Collection already exists.");
      return;
    }

    await qdrantClient.createCollection(COLLECTION_NAME, {
      vectors: {
        size: 1024,
        distance: "Cosine",
      },
    });

    console.log("Qdrant collection created successfully!");
  } catch (error) {
    console.error("Collection creation failed:", error.message);
  }
}

createCollection();