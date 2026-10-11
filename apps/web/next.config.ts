import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // CLAUDE.md is the only rules file for agents in this repository.
  agentRules: false,
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
