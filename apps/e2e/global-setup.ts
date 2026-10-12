import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const API_DIR = resolve(import.meta.dirname, "../api");

/** Every run starts from an empty database, so it can be repeated. */
export default function globalSetup(): void {
  execFileSync(".venv/bin/python", [resolve(import.meta.dirname, "reset_db.py")], {
    cwd: API_DIR,
    // The script lives here, but what it imports is the API's.
    env: { ...process.env, PYTHONPATH: API_DIR },
    stdio: "inherit",
  });
}
