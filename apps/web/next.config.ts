import { withSerwist } from "@serwist/turbopack";
import { withRelatedProject } from "@vercel/related-projects";
import type { NextConfig } from "next";

// The browser only ever talks to the web's own origin; Next.js forwards /api to FastAPI.
// On Vercel the address comes from the API project linked in vercel.json, so each
// preview of the web reaches the preview of the API on the same branch. Elsewhere it
// is API_URL.
const apiUrl = withRelatedProject({
  projectName: "arrendi-api",
  defaultHost: process.env.API_URL ?? "http://localhost:8000",
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
