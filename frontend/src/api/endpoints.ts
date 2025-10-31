const ASSISTANT_BASE = "/assistant" as const;

export const endpoints = {
  assistant: {
    sessions: () => `${ASSISTANT_BASE}/sessions`,
    sessionHistory: (sessionId: string) => `${ASSISTANT_BASE}/sessions/${sessionId}/history`,
    messages: () => `${ASSISTANT_BASE}/messages`
  }
} as const;

export type AssistantEndpointKey = keyof typeof endpoints.assistant;
