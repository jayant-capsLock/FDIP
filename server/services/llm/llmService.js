
import getProvider from "./providerFactory.js";

const llmService = {
  generateAnswer: async (options) => {
    const provider = getProvider();

    return provider.generateAnswer(options);
  },
};

export default llmService;
