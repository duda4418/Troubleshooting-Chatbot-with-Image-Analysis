const ASSISTANT_BASE = "/assistant" as const;
const METRICS_BASE = "/metrics" as const;

export const endpoints = {
  assistant: {
    sessions: () => `${ASSISTANT_BASE}/sessions`,
    sessionHistory: (sessionId: string) => `${ASSISTANT_BASE}/sessions/${sessionId}/history`,
    messages: () => `${ASSISTANT_BASE}/messages`,
    sessionFeedback: (sessionId: string) => `${ASSISTANT_BASE}/sessions/${sessionId}/feedback`
  },
  metrics: {
    usage: () => `${METRICS_BASE}/usage`
  }
} as const;

export type AssistantEndpointKey = keyof typeof endpoints.assistant;
export type MetricsEndpointKey = keyof typeof endpoints.metrics;
