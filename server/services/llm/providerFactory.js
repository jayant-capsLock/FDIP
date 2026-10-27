
import openrouterProvider from "./providers/openrouterProvider.js";

const providers = {
  openrouter: openrouterProvider,
};

const getProvider = () => {
  const providerName = (
    process.env.LLM_PROVIDER || "openrouter"
  ).toLowerCase();

  const provider = providers[providerName];

  if (!provider) {
    throw new Error(`Unsupported LLM provider: ${providerName}`);
  }

  return provider;
};

export default getProvider;
