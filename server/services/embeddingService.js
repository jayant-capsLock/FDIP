
import jinaProvider from "./embeddings/jinaProvider.js";

const providers = {
  jina: jinaProvider,
};

const providerName = process.env.EMBEDDING_PROVIDER || "jina";

const provider = providers[providerName];

if (!provider) {
  throw new Error(`Unsupported embedding provider: ${providerName}`);
}

const embeddingService = {
  generateEmbeddings: (texts) => {
    return provider.generateEmbeddings(texts);
  },

  getDimensions: () => {
    return provider.getDimensions();
  },

  getModelName: () => {
    return provider.getModelName();
  },
};

export default embeddingService;
