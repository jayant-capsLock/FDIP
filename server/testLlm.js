import "dotenv/config";
import llmService from "./services/llm/llmService.js";

const testLLM = async () => {
  try {
    const answer = await llmService.generateAnswer({
      messages: [
        {
          role: "system",
          content: "You are a helpful financial document assistant.",
        },
        {
          role: "user",
          content: "What is an invoice? Explain in two sentences.",
        },
      ],
    });

    console.log("\nLLM RESPONSE:\n");
    console.log(answer);
  } catch (error) {
    console.error("LLM TEST FAILED:", error.message);
  }
};

testLLM();