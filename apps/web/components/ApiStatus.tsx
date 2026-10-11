"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";

// Provisional: shows that the web reaches the API, until the first real screen calls it.
export function ApiStatus() {
  const [status, setStatus] = useState<"checking" | "ok" | "down">("checking");

  useEffect(() => {
    api
      .GET("/api/health")
      .then(({ data }) => setStatus(data?.status === "ok" ? "ok" : "down"))
      .catch(() => setStatus("down"));
  }, []);

  const text = {
    checking: "Comprobando la conexión con la API…",
    ok: "Conectada con la API.",
    down: "No hay conexión con la API.",
  }[status];

  return (
    <p role="status" className="text-support text-muted-foreground">
      {text}
    </p>
  );
}
