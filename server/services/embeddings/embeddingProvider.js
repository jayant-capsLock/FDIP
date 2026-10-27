const embeddingProvider = {
  generateEmbeddings: async (texts) => {
    throw new Error("Embedding provider not configured");
  },

  getDimensions: () => {
    throw new Error("Embedding provider not configured");
  },

  getModelName: () => {
    throw new Error("Embedding provider not configured");
  },
};

export default embeddingProvider;
