import { withSerwist } from "@serwist/turbopack";
import { withRelatedProject } from "@vercel/related-projects";
import type { NextConfig } from "next";

// The browser only ever talks to the web's own origin; Next.js forwards /api to FastAPI.
// API_URL wins when it is set, so an environment can point at a fixed API (custom domain).
// Without it, on Vercel the address comes from the API project linked in vercel.json, so
// each preview of the web reaches the preview of the API on the same branch. Elsewhere it
// falls back to the local API.
const apiUrl =
  process.env.API_URL ??
  withRelatedProject({
    projectName: "arrendi-api",
    defaultHost: "http://localhost:8000",
  });

const nextConfig: NextConfig = {
  // The end-to-end run builds into its own folder, next to a `pnpm dev` that is open.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
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

export default withSerwist(nextConfig);
