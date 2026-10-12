// Stands in for the two parts of Supabase the app talks to: Auth and Storage.
//
// Only what the web and the API really call. Auth signs tokens with a key made on start
// and publishes it by JWKS, so the API and Next.js verify them exactly as they verify
// Supabase's. Storage keeps the files in memory. Nothing here leaves this computer.

import { createHash, generateKeyPairSync, randomUUID, sign } from "node:crypto";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";

import { SUPABASE_PORT, SUPABASE_URL } from "../ports.ts";

const ISSUER = `${SUPABASE_URL}/auth/v1`;
const KEY_ID = "e2e-key";
const { privateKey, publicKey } = generateKeyPairSync("ec", { namedCurve: "P-256" });

const base64url = (data: Buffer | string) => Buffer.from(data).toString("base64url");

/** The same person always gets the same id, like a real account would. */
function userId(email: string): string {
  const hex = createHash("sha256").update(email).digest("hex");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-8${hex.slice(17, 20)}-${hex.slice(20, 32)}`;
}

function user(email: string) {
  const now = new Date().toISOString();
  return {
    id: userId(email),
    aud: "authenticated",
    role: "authenticated",
    email,
    email_confirmed_at: now,
    confirmed_at: now,
    last_sign_in_at: now,
    app_metadata: { provider: "email", providers: ["email"] },
    user_metadata: { full_name: "Ana Prueba", email },
    identities: [],
    created_at: now,
    updated_at: now,
    is_anonymous: false,
  };
}

function accessToken(email: string, expiresAt: number): string {
  const header = { alg: "ES256", typ: "JWT", kid: KEY_ID };
  const claims = {
    iss: ISSUER,
    sub: userId(email),
    aud: "authenticated",
    exp: expiresAt,
    iat: Math.floor(Date.now() / 1000),
    email,
    role: "authenticated",
    aal: "aal1",
    session_id: randomUUID(),
    is_anonymous: false,
    app_metadata: { provider: "email", providers: ["email"] },
    user_metadata: { full_name: "Ana Prueba", email },
  };
  const signed = `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(claims))}`;
  // JWTs carry the raw r and s of the signature, not the DER that Node makes by default.
  const signature = sign("sha256", Buffer.from(signed), {
    key: privateKey,
    dsaEncoding: "ieee-p1363",
  });
  return `${signed}.${base64url(signature)}`;
}

function session(email: string) {
  const expiresIn = 3600;
  const expiresAt = Math.floor(Date.now() / 1000) + expiresIn;
  return {
    access_token: accessToken(email, expiresAt),
    token_type: "bearer",
    expires_in: expiresIn,
    expires_at: expiresAt,
    // The refresh token only has to bring back who it belongs to.
    refresh_token: base64url(email),
    user: user(email),
  };
}

/** Who a request is from, read from its token without checking it: this is a stand-in. */
function emailOf(request: IncomingMessage): string | undefined {
  const token = request.headers.authorization?.replace(/^Bearer /, "");
  try {
    return JSON.parse(Buffer.from(token!.split(".")[1], "base64url").toString()).email;
  } catch {
    return undefined;
  }
}

async function body(request: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(chunk as Buffer);
  return Buffer.concat(chunks);
}

function json(response: ServerResponse, status: number, data: unknown): void {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(data));
}

async function auth(request: IncomingMessage, response: ServerResponse, url: URL): Promise<void> {
  const route = `${request.method} ${url.pathname.replace("/auth/v1", "")}`;
  if (route === "GET /.well-known/jwks.json") {
    const key = { ...publicKey.export({ format: "jwk" }), kid: KEY_ID, alg: "ES256", use: "sig" };
    return json(response, 200, { keys: [key] });
  }
  if (route === "POST /token") {
    const sent = JSON.parse((await body(request)).toString() || "{}");
    const email =
      url.searchParams.get("grant_type") === "refresh_token"
        ? Buffer.from(sent.refresh_token ?? "", "base64url").toString()
        : sent.email;
    // Any password opens the door: there is nothing behind it but test data.
    if (!email) return json(response, 400, { code: 400, msg: "missing email" });
    return json(response, 200, session(email));
  }
  if (route === "GET /user") {
    const email = emailOf(request);
    return email ? json(response, 200, user(email)) : json(response, 401, { msg: "no session" });
  }
  if (route === "POST /logout") {
    response.writeHead(204).end();
    return;
  }
  json(response, 404, { msg: `the fake auth has no ${route}` });
}

const files = new Map<string, Buffer>();
const TYPES: Record<string, string> = {
  pdf: "application/pdf",
  jpg: "image/jpeg",
  png: "image/png",
};

function sendFile(response: ServerResponse, path: string): void {
  const file = files.get(path);
  if (!file) return json(response, 404, { error: "not_found" });
  const type = TYPES[path.split(".").pop() ?? ""] ?? "application/octet-stream";
  response.writeHead(200, { "content-type": type, "content-length": file.length });
  response.end(file);
}

async function storage(
  request: IncomingMessage,
  response: ServerResponse,
  url: URL,
): Promise<void> {
  // "/storage/v1/object/<kind>/<bucket>/<path>", where <kind> may be missing.
  const rest = decodeURIComponent(url.pathname.replace("/storage/v1/object/", ""));
  const method = request.method;
  // The path inside the bucket, once the prefix and the bucket's name are taken away.
  const after = (prefix: string) => rest.slice(prefix.length).split("/").slice(1).join("/");

  if (rest.startsWith("upload/sign/")) {
    const path = after("upload/sign/");
    if (method === "POST") {
      return json(response, 200, { url: `${url.pathname.replace("/storage/v1", "")}?token=e2e` });
    }
    // The browser, with the signed link. It never replaces a file that is already there.
    if (files.has(path)) return json(response, 400, { error: "Duplicate" });
    files.set(path, await body(request));
    return json(response, 200, { Key: path });
  }
  if (rest.startsWith("info/")) {
    const file = files.get(after("info/"));
    return file ? json(response, 200, { size: file.length }) : json(response, 404, {});
  }
  if (rest.startsWith("sign/")) {
    if (method === "POST") {
      return json(response, 200, {
        signedURL: `${url.pathname.replace("/storage/v1", "")}?token=e2e`,
      });
    }
    return sendFile(response, after("sign/"));
  }
  if (method === "DELETE") {
    const { prefixes = [] } = JSON.parse((await body(request)).toString() || "{}");
    for (const path of prefixes) files.delete(path);
    return json(response, 200, []);
  }
  const path = rest.split("/").slice(1).join("/");
  if (method === "POST") {
    // The API, with files it made itself; it may replace the one there.
    files.set(path, await body(request));
    return json(response, 200, { Key: path });
  }
  sendFile(response, path);
}

createServer(async (request, response) => {
  // The browser calls from the web's origin.
  response.setHeader("access-control-allow-origin", "*");
  response.setHeader("access-control-allow-headers", "*");
  response.setHeader("access-control-allow-methods", "GET, POST, PUT, DELETE, OPTIONS");
  if (request.method === "OPTIONS") {
    response.writeHead(204).end();
    return;
  }
  const url = new URL(request.url ?? "/", SUPABASE_URL);
  try {
    if (url.pathname === "/health") return json(response, 200, { ok: true });
    if (url.pathname.startsWith("/auth/v1/")) return await auth(request, response, url);
    if (url.pathname.startsWith("/storage/v1/object/")) {
      return await storage(request, response, url);
    }
    json(response, 404, { msg: `the fake Supabase has no ${url.pathname}` });
  } catch (error) {
    json(response, 500, { msg: String(error) });
  }
}).listen(SUPABASE_PORT, () => console.log(`fake Supabase on ${SUPABASE_URL}`));
