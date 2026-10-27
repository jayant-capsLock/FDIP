
import llmService from "./llm/llmService.js";

const ragService = {
  generateAnswer: async (question, chunks) => {
    const context = chunks.map((chunk, index) => {
      return `
[SOURCE ${index + 1}]
Document: ${chunk.document_name}
Page: ${chunk.page_start || "Unknown"}
Content:
${chunk.chunk_text}
`;
    }).join("\n");

    const messages = [
      {
        role: "system",
        content: `
You are FDIP, a financial document assistant.

Answer the user's question using ONLY the provided document context.

Rules:
1. Do not invent financial figures or facts.
2. If the context does not contain the answer, say so.
3. Cite your sources using [SOURCE 1], [SOURCE 2], etc.
4. Be clear and concise.
5. Never assume missing information.
        `,
      },
      {
        role: "user",
        content: `
DOCUMENT CONTEXT:

${context}

USER QUESTION:

${question}
        `,
      },
    ];

    return llmService.generateAnswer({
      messages,
      temperature: 0.2,
      maxTokens: 1200,
    });
  },
};

export default ragService;
