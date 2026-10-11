import type { NextConfig } from "next";

// The browser only ever talks to the web's own origin; Next.js forwards /api to FastAPI.
const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // CLAUDE.md is the only rules file for agents in this repository.
  agentRules: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
