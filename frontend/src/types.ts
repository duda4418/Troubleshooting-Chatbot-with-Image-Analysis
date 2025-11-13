export type MessageRole = "user" | "assistant" | "system" | "tool";

export type ConversationStatus = "in_progress" | "resolved" | "escalated" | "needs_attention";

export interface ToolCallMetadata {
  tool?: string;
  summary?: string;
  success?: boolean;
  [key: string]: unknown;
}

export interface KnowledgeHit {
  label: string;
  similarity: number;
  summary: string;
  steps: string[];
}

export interface FollowUpOption {
  value: string;
  label: string;
}

export type FollowUpFieldType =
  | "boolean"
  | "yes_no"
  | "text"
  | "textarea"
  | "number"
  | "single_select"
  | "multi_select"
  | "image";

export interface FollowUpField {
  id: string;
  label: string;
  type: FollowUpFieldType;
  required?: boolean;
  helper_text?: string;
  placeholder?: string;
  options?: FollowUpOption[];
}

export type FollowUpFormStatus = "in_progress" | "submitted" | "dismissed";

export interface FollowUpFormSubmissionField {
  id: string;
  label: string;
  type: FollowUpFieldType;
  value: string | number | string[] | null;
  attachments?: Array<{ name: string; mime_type?: string; size_bytes?: number }>;
}

export interface FollowUpFormSubmissionState {
  replied_to?: string;
  status?: FollowUpFormStatus;
  submitted_at?: string;
  fields: FollowUpFormSubmissionField[];
}

export interface FollowUpFormDescriptor {
  id?: string;
  title?: string;
  description?: string | null;
  status?: FollowUpFormStatus;
  submitted_at?: string | null;
  rejected_at?: string | null;
  rejection_reason?: string | null;
  fields: FollowUpField[];
  submission?: FollowUpFormSubmissionState;
}

export interface MessageAttachmentMetadata {
  type: "image" | string;
  name?: string;
  mime_type?: string;
  url?: string;
  base64?: string;
}

export interface MessageMetadata {
  suggested_actions?: string[];
  knowledge_hits?: KnowledgeHit[];
  confidence?: number;
  tool_results?: ToolCallMetadata[];
  needs_more_info?: boolean;
  escalate?: boolean;
  has_image?: boolean;
  image_mime_type?: string;
  image_file_name?: string;
  image_url?: string;
  image_count?: number;
  images_b64?: string[];
  attachments?: MessageAttachmentMetadata[];
  follow_up_form?: FollowUpFormDescriptor;
  follow_up_form_submission?: FollowUpFormSubmissionState;
  form_id?: string;
  follow_up_questions?: string[];
  follow_up_form_summary?: string;
  client_hidden?: boolean;
  extra?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  metadata: MessageMetadata;
  status?: "pending" | "failed";
}

export interface ConversationSession {
  id: string;
  status: ConversationStatus;
  createdAt: string;
  updatedAt: string;
  title: string;
  lastUpdatedLabel: string;
  endedAt?: string | null;
  feedbackRating?: number | null;
}

export interface ConversationHistory {
  session: ConversationSession;
  messages: ChatMessage[];
}
