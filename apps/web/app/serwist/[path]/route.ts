import { createSerwistRoute } from "@serwist/turbopack";

// Builds the service worker and serves it at /serwist/sw.js. With Turbopack, Serwist
// cannot write it to `public/`, so it comes from this route, generated at build time.
// There are no business rules here.

// The offline page must be re-fetched whenever a new version is published.
const revision = process.env.VERCEL_GIT_COMMIT_SHA ?? crypto.randomUUID();

export const { dynamic, dynamicParams, revalidate, generateStaticParams, GET } = createSerwistRoute({
  swSrc: "app/sw.ts",
  additionalPrecacheEntries: [{ url: "/~offline", revision }],
  useNativeEsbuild: true,
});
