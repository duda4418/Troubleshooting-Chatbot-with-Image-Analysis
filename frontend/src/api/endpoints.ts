const ASSISTANT_BASE = "/assistant" as const;

export const endpoints = {
  assistant: {
    sessions: () => `${ASSISTANT_BASE}/sessions`,
    sessionHistory: (sessionId: string) => `${ASSISTANT_BASE}/sessions/${sessionId}/history`,
    messages: () => `${ASSISTANT_BASE}/messages`,
    sessionFeedback: (sessionId: string) => `${ASSISTANT_BASE}/sessions/${sessionId}/feedback`
  }
} as const;

export type AssistantEndpointKey = keyof typeof endpoints.assistant;
