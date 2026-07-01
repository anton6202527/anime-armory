import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri expects a fixed port and does not want Vite to clear the screen.
// https://v2.tauri.app/start/frontend/vite/
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: false,
    watch: {
      // don't watch the Rust side from Vite
      ignored: ["**/src-tauri/**"],
    },
  },
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    target: "es2021",
    sourcemap: true,
    // Monaco is an intentional, lazy-loaded editor runtime. Keep the generic
    // warning focused on unexpected chunks instead of the known editor payload.
    chunkSizeWarningLimit: 4096,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("monaco-editor")) return "vendor-monaco";
          if (id.includes("@xterm")) return "vendor-terminal";
          if (id.includes("@xyflow")) return "vendor-canvas";
          if (id.includes("node_modules/react")) return "vendor-react";
        },
      },
    },
  },
});
