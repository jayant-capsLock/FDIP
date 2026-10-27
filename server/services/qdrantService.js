
import qdrantClient from "../config/qdrantClient.js";

const COLLECTION_NAME = "fdip_document_chunks";

const qdrantService = {
  upsertChunks: async (chunks, embeddings) => {
    if (chunks.length !== embeddings.length) {
      throw new Error("Chunks and embeddings count mismatch");
    }

    const points = chunks.map((chunk, index) => ({
      id: chunk.id,
      vector: embeddings[index],
      payload: {
        document_id: chunk.document_id,
        chunk_index: chunk.chunk_index,
        chunk_text: chunk.chunk_text,
        char_count: chunk.char_count,
        page_start: chunk.page_start,
        page_end: chunk.page_end,
      },
    }));

    await qdrantClient.upsert(COLLECTION_NAME, {
      wait: true,
      points,
    });

    console.log(`Stored ${points.length} chunks in Qdrant.`);
  },
};

export default qdrantService;
