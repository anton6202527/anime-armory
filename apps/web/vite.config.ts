import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { viteCanvasGenerationPlugin } from "./vite.canvasGeneration";

export default defineConfig(({ mode }) => {
  const fileEnvironment = loadEnv(mode, process.cwd(), "");
  const serverEnvironment = (name: string): string | undefined => process.env[name] ?? fileEnvironment[name];
  const environment = {
    CLI_PROXY_API_URL: serverEnvironment("CLI_PROXY_API_URL"),
    CLI_PROXY_API_KEY: serverEnvironment("CLI_PROXY_API_KEY"),
    CUSTOM_OPENAI_BASE_URL: serverEnvironment("CUSTOM_OPENAI_BASE_URL"),
    CUSTOM_OPENAI_API_KEY: serverEnvironment("CUSTOM_OPENAI_API_KEY"),
    VITE_CLI_PROXY_API_KEY: serverEnvironment("VITE_CLI_PROXY_API_KEY"),
    VITE_CUSTOM_OPENAI_API_KEY: serverEnvironment("VITE_CUSTOM_OPENAI_API_KEY"),
  };
  return {
    plugins: [react(), viteCanvasGenerationPlugin(environment)],
    server: {
      host: "127.0.0.1",
      port: 4174,
    },
  };
});
