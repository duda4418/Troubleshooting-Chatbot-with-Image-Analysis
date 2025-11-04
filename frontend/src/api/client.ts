import axios from "axios";

const DEFAULT_API_PORT = 8000;
const API_APPS_BASE = "azurecontainerapps.io";

const resolveBaseUrl = (): string => {
  const envValue = import.meta.env.VITE_API_BASE_URL as string | undefined;

  if (envValue) {
    // Allow relative paths such as "/api" to pass straight through.
    if (envValue.startsWith("/")) {
      return envValue.replace(/\/$/, "");
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
    const { protocol, hostname, port } = window.location;

    const backendUrlOverride = import.meta.env.VITE_BACKEND_URL as string | undefined;
    if (backendUrlOverride) {
      return backendUrlOverride.replace(/\/$/, "");
    }

    const backendHostName = import.meta.env.VITE_BACKEND_HOSTNAME as string | undefined;
    if (backendHostName) {
      return `${protocol}//${backendHostName.replace(/\/$/, "")}`;
    }

    if (hostname.endsWith(API_APPS_BASE)) {
      const hostParts = hostname.split(".");
      if (hostParts.length > 1) {
        const backendAppName = (import.meta.env.VITE_BACKEND_HOST ?? "server-app").trim();
        hostParts[0] = backendAppName || "server-app";
        return `${protocol}//${hostParts.join(".")}`;
      }
    }

    if (port) {
      return `${protocol}//${hostname}:${port}`;
    }

    return `${protocol}//${hostname}`;
  }

  const backendHost = import.meta.env.VITE_BACKEND_HOST ?? "server-app";
  return `https://${backendHost}.${API_APPS_BASE}`;
};

const apiClient = axios.create({
  baseURL: resolveBaseUrl(),
  headers: {
    "Content-Type": "application/json"
  }
});

export default apiClient;
