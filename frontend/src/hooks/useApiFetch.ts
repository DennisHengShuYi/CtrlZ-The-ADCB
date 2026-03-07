import { useAuth } from "@clerk/clerk-react";
import { useCallback } from "react";
import { apiFetch } from "../lib/api";

/**
 * Hook that returns a fetch function pre-bound with the Clerk token.
 */
export function useApiFetch() {
  const { getToken } = useAuth();

  const authenticatedFetch = useCallback(
    async (path: string, options: RequestInit = {}) => {
      const isMockMode = localStorage.getItem("Mock-Mode") === "true";
      let token = null;
      if (!isMockMode) {
        token = await getToken();
      }
      return apiFetch(path, options, token);
    },
    [getToken],
  );

  return authenticatedFetch;
}
