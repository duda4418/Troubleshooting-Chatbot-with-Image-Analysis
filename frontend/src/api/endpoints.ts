const ASSISTANT_BASE = "/assistant" as const;
const METRICS_BASE = "/metrics" as const;
const CATALOGUE_BASE = "/catalogue" as const;

export const endpoints = {
  assistant: {
    sessions: () => `${ASSISTANT_BASE}/sessions`,
    sessionHistory: (sessionId: string) => `${ASSISTANT_BASE}/sessions/${sessionId}/history`,
    messages: () => `${ASSISTANT_BASE}/messages`,
    sessionFeedback: (sessionId: string) => `${ASSISTANT_BASE}/sessions/${sessionId}/feedback`
  },
  metrics: {
    usage: () => `${METRICS_BASE}/usage`
  },
  catalogue: {
    categories: () => `${CATALOGUE_BASE}/categories`,
    category: (categoryId: string) => `${CATALOGUE_BASE}/categories/${categoryId}`,
    causes: () => `${CATALOGUE_BASE}/causes`,
    cause: (causeId: string) => `${CATALOGUE_BASE}/causes/${causeId}`,
    solutions: () => `${CATALOGUE_BASE}/solutions`,
    solution: (solutionId: string) => `${CATALOGUE_BASE}/solutions/${solutionId}`,
    import: () => `/troubleshooting/import`
  }
} as const;

export type AssistantEndpointKey = keyof typeof endpoints.assistant;
export type MetricsEndpointKey = keyof typeof endpoints.metrics;
export type CatalogueEndpointKey = keyof typeof endpoints.catalogue;
