"use client";

import { useCallback, useEffect, useState } from "react";

import type { ApiError } from "./client";
import { apiErrorMessage, CONNECTION_ERROR } from "./errors";

type Loaded<T> = {
  /** Undefined while loading, and when it failed. */
  data: T | undefined;
  /** A message for the owner when the load failed. */
  error: string | undefined;
  /** True when the API said the resource does not exist (or belongs to someone else). */
  notFound: boolean;
  reload: () => void;
};

type Result<T> = { data?: T; error?: ApiError; response: Response };

/**
 * Loads something from the API when the screen opens.
 *
 * `load` must keep its identity between renders (wrap it in `useCallback`), or the
 * screen loads again on every render.
 */
export function useLoad<T>(load: () => Promise<Result<T>>): Loaded<T> {
  const [state, setState] = useState<Omit<Loaded<T>, "reload">>({
    data: undefined,
    error: undefined,
    notFound: false,
  });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    load()
      .then(({ data, error, response }) => {
        if (!current) return;
        if (data !== undefined) setState({ data, error: undefined, notFound: false });
        else
          setState({
            data: undefined,
            error: apiErrorMessage(error),
            notFound: response.status === 404,
          });
      })
      .catch(() => {
        if (current) setState({ data: undefined, error: CONNECTION_ERROR, notFound: false });
      });
    return () => {
      current = false;
    };
  }, [load, attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  return { ...state, reload };
}
