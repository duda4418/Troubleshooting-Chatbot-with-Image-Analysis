import axios from "axios";

const DEFAULT_API_PORT = 8000;

const resolveBaseUrl = (): string => {
  const envValue = import.meta.env.VITE_API_BASE_URL as string | undefined;

  if (envValue) {
    // Allow relative paths such as "/api" to pass straight through.
    if (envValue.startsWith("/")) {
      return envValue;
    }

    try {
      const url = new URL(envValue);
      if (typeof window !== "undefined") {
        const shouldRewriteHost = ["backend", "api", "backend.local"].includes(url.hostname.toLowerCase());
        if (shouldRewriteHost) {
          const port = url.port || `${DEFAULT_API_PORT}`;
          return `${window.location.protocol}//${window.location.hostname}:${port}${url.pathname}`.replace(/\/$/, "");
        }
      }
      return envValue;
    } catch (error) {
      console.warn("Invalid VITE_API_BASE_URL provided, falling back to auto detection", error);
    }
  }

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:${DEFAULT_API_PORT}`;
  }

  return `http://127.0.0.1:${DEFAULT_API_PORT}`;
};

const apiClient = axios.create({
  baseURL: resolveBaseUrl(),
  headers: {
    "Content-Type": "application/json"
  }
});

export default apiClient;
