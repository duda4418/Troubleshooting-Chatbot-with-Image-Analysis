import apiClient from "./client";
import { endpoints } from "./endpoints";

export interface ApiConversationSession {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  ended_at?: string | null;
}

export interface ApiConversationMessage {
  id: string;
  session_id: string;
  role: string;
  content: string;
  message_metadata: Record<string, unknown>;
  created_at: string;
  helpful?: boolean | null;
}

export interface ApiConversationHistoryResponse {
  session: ApiConversationSession;
  history: ApiConversationMessage[];
}

export interface AssistantMessagePayload {
  session_id?: string | null;
  text?: string | null;
  images_b64?: string[];
  image_mime_types?: (string | null)[];
  locale?: string;
  metadata?: Record<string, unknown>;
}

export interface AssistantFormFieldPayload {
  question: string;
  input_type: string;
  required?: boolean;
  placeholder?: string | null;
  options?: Array<{ value: string; label: string }>;
}

export interface AssistantFormPayload {
  title?: string;
  description?: string | null;
  fields: AssistantFormFieldPayload[];
}

export interface AssistantAnswerPayload {
  reply: string;
  suggested_actions: string[];
  follow_up_form?: AssistantFormPayload | null;
  confidence?: number | null;
  metadata: Record<string, unknown>;
}

export interface KnowledgeHitPayload {
  label: string;
  similarity: number;
  summary: string;
  steps: string[];
}

export interface AssistantMessageResponse {
  session_id: string;
  user_message_id: string;
  assistant_message_id: string;
  answer: AssistantAnswerPayload;
  knowledge_hits: KnowledgeHitPayload[];
  form_id?: string | null;
}

export const fetchSessions = async (limit = 50): Promise<ApiConversationSession[]> => {
  const { data } = await apiClient.get<ApiConversationSession[]>(endpoints.assistant.sessions(), {
    params: { limit }
  });
  return data;
};

export const fetchSessionHistory = async (
  sessionId: string,
  limit = 100
): Promise<ApiConversationHistoryResponse> => {
  const { data } = await apiClient.get<ApiConversationHistoryResponse>(
    endpoints.assistant.sessionHistory(sessionId),
    {
      params: { limit }
    }
  );
  return data;
};

export const sendAssistantMessage = async (
  payload: AssistantMessagePayload
): Promise<AssistantMessageResponse> => {
  const { data } = await apiClient.post<AssistantMessageResponse>(endpoints.assistant.messages(), payload);
  return data;
};
