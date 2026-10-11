"use client";

import { useCallback, useState } from "react";

import type { ApiError } from "./client";
import { apiErrorMessage, CONNECTION_ERROR } from "./errors";

type Result<T> = { data?: T; error?: ApiError };

/**
 * Runs a request that changes something, and keeps what a form needs to show:
 * whether it is in flight and what went wrong.
 *
 * `save` returns the data when it worked and undefined when it did not; `saving` stays
 * true after a success, because the screen is about to leave and a second tap must not
 * send it twice.
 */
export function useSave() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  const save = useCallback(async <T>(request: () => Promise<Result<T>>): Promise<T | undefined> => {
    setSaving(true);
    setError(undefined);
    try {
      const { data, error } = await request();
      if (data !== undefined) return data;
      setError(apiErrorMessage(error));
    } catch {
      setError(CONNECTION_ERROR);
    }
    setSaving(false);
    return undefined;
  }, []);

  return { save, saving, error };
}
