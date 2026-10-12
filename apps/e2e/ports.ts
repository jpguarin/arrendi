// Ports of their own, so the end-to-end run can sit next to `pnpm dev` (3000 and 8000).
export const WEB_PORT = 3100;
export const API_PORT = 8100;
export const SUPABASE_PORT = 54399;

export const WEB_URL = `http://localhost:${WEB_PORT}`;
export const API_URL = `http://localhost:${API_PORT}`;
export const SUPABASE_URL = `http://localhost:${SUPABASE_PORT}`;
