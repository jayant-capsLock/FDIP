
import axios from "axios";

const API_URL = "https://openrouter.ai/api/v1/chat/completions";

const openrouterProvider = {
  generateAnswer: async ({
    messages,
    temperature = 0.2,
    maxTokens = 1000,
  }) => {
    try {
      const { data } = await axios.post(
        API_URL,
        {
          model: process.env.OPENROUTER_MODEL,
          messages,
          temperature,
          max_tokens: maxTokens,
        },
        {
          headers: {
            Authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`,
            "Content-Type": "application/json",
          },
        },
      );

      return data.choices[0].message.content;
    } catch (error) {
      console.error(
        "OpenRouter API Error:",
        error.response?.data || error.message,
      );

      throw new Error("Failed to generate answer using OpenRouter");
    }
  },
};

export default openrouterProvider;
