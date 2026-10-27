import axios from "axios";

const API_URL = "https://api.jina.ai/v1/embeddings";

const MODEL = "jina-embeddings-v5-text-small";
const DIMENSIONS = 1024;

const jinaProvider = {
  generateEmbeddings: async (texts, task = "retrieval.passage") => {
    const { data } = await axios.post(
      API_URL,
      {
        model: MODEL,
        task,
        dimensions: DIMENSIONS,
        input: texts,
      },
      {
        headers: {
          Authorization: `Bearer ${process.env.JINA_API_KEY}`,
          "Content-Type": "application/json",
        },
      },
    );

    return data.data.map((item) => item.embedding);
  },

  getDimensions: () => DIMENSIONS,

  getModelName: () => MODEL,
};

export default jinaProvider;
