
import embeddingService from "./embeddingService.js";
import qdrantClient from "../config/qdrantClient.js";

const COLLECTION_NAME = "fdip_document_chunks";

const retrievalService = {
  searchChunks: async (
    queryText,
    limit = 5,
    documentId = null,
    allowedDocumentIds = null
  ) => {
    if (!queryText || !queryText.trim()) {
      throw new Error("Search query cannot be empty");
    }

    // Generate query embedding
    const [queryEmbedding] =
      await embeddingService.generateEmbeddings(
        [queryText],
        "retrieval.query"
      );

    const searchOptions = {
      query: queryEmbedding,
      limit,
      with_payload: true,
    };

    // Search within one specific document
    if (documentId) {
      searchOptions.filter = {
        must: [
          {
            key: "document_id",
            match: { value: documentId },
          },
        ],
      };
    }
    // Search only within the user's permitted documents
    else if (allowedDocumentIds) {
      if (allowedDocumentIds.length === 0) {
        return [];
      }

      searchOptions.filter = {
        should: allowedDocumentIds.map((id) => ({
          key: "document_id",
          match: { value: id },
        })),
      };
    }

    const results = await qdrantClient.query(
      COLLECTION_NAME,
      searchOptions
    );

    return results.points.map((point) => ({
      id: point.id,
      score: point.score,
      ...point.payload,
    }));
  },
};

export default retrievalService;
