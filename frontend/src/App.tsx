import { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, Route, Routes, useMatch, useNavigate } from "react-router-dom";
import Header from "layout/Header";
import Footer from "layout/Footer";
import NotificationOverlay from "components/NotificationOverlay";
import ConversationDashboardPage from "pages/ConversationDashboardPage";
import ConversationDetailPage from "pages/ConversationDetailPage";
import {
  fetchSessions,
  fetchSessionHistory,
  sendAssistantMessage,
  submitSessionFeedback,
  type ApiConversationHistoryResponse,
  type ApiConversationMessage,
  type ApiConversationSession
} from "./api/assistant";
import type {
  ChatMessage,
  ConversationSession,
  FollowUpField,
  FollowUpFormDescriptor,
  FollowUpFormSubmissionField,
  FollowUpFormSubmissionState,
  FollowUpFormStatus,
  FollowUpOption,
  KnowledgeHit,
  MessageMetadata,
  ToolCallMetadata
} from "./types";

const sessionDateFormatter = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "short"
});

const truncate = (value: string, max = 56) => {
  if (value.length <= max) return value;
  return `${value.slice(0, max).trim()}…`;
};

const coerceStringArray = (value: unknown): string[] | undefined => {
  if (!Array.isArray(value)) return undefined;
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
};

const coerceToolResults = (value: unknown): ToolCallMetadata[] | undefined => {
  if (!Array.isArray(value)) return undefined;
  return value
    .map((entry) => (typeof entry === "object" && entry !== null ? (entry as ToolCallMetadata) : undefined))
    .filter((entry): entry is ToolCallMetadata => Boolean(entry));
};

const parseKnowledgeHits = (value: unknown): KnowledgeHit[] | undefined => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  const hits = value
    .map((entry) => {
      if (!entry || typeof entry !== "object") {
        return null;
      }
      const payload = entry as Record<string, unknown>;
      const label = typeof payload.label === "string" ? payload.label : undefined;
      const similarity = typeof payload.similarity === "number" ? payload.similarity : undefined;
      const summary = typeof payload.summary === "string" ? payload.summary : undefined;
      const steps = coerceStringArray(payload.steps) ?? [];
      if (!label || similarity === undefined || !summary) {
        return null;
      }
      return {
        label,
        similarity,
        summary,
        steps,
      } satisfies KnowledgeHit;
    })
    .filter((hit): hit is KnowledgeHit => Boolean(hit));

  return hits.length ? hits : undefined;
};

const parseAttachments = (value: unknown): MessageMetadata["attachments"] => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  const attachments = value
    .map((entry) => {
      if (!entry || typeof entry !== "object") {
        return null;
      }
      const payload = entry as Record<string, unknown>;
      const type = typeof payload.type === "string" ? payload.type : "attachment";
      const name = typeof payload.name === "string" ? payload.name : undefined;
      const mime_type = typeof payload.mime_type === "string" ? payload.mime_type : undefined;
      const url = typeof payload.url === "string" ? payload.url : undefined;
      const base64 = typeof payload.base64 === "string" ? payload.base64 : undefined;
      return {
        type,
        name,
        mime_type,
        url,
        base64,
      };
    })
    .filter((attachment) => attachment !== null);

  return attachments.length ? (attachments as MessageMetadata["attachments"]) : undefined;
};

const coerceFormStatus = (value: unknown): FollowUpFormStatus | undefined => {
  if (typeof value !== "string") {
    return undefined;
  }
  const normalized = value.toLowerCase();
  if (["in_progress", "submitted", "dismissed"].includes(normalized)) {
    return normalized as FollowUpFormStatus;
  }
  if (normalized === "ignored") {
    return "dismissed";
  }
  return undefined;
};

const normalizeFieldType = (value: unknown): FollowUpField["type"] => {
  const normalized = typeof value === "string" ? value.toLowerCase() : "";
  switch (normalized) {
    case "textarea":
      return "textarea";
    case "number":
      return "number";
    case "multi_select":
    case "multiselect":
    case "checkboxes":
      return "multi_select";
    case "single_select":
    case "select":
    case "dropdown":
    case "single_choice":
      return "single_select";
    case "boolean":
    case "yes_no":
    case "yesno":
      return "yes_no";
    case "image":
    case "photo":
      return "image";
    case "text":
    default:
      return "text";
  }
};

const buildFieldId = (question: unknown, index: number): string => {
  if (typeof question === "string" && question.trim().length) {
    const slug = question
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 32);
    if (slug) {
      return `${slug}-${index}`;
    }
  }
  return `field-${index}`;
};

const parseFollowUpFormFields = (value: unknown): FollowUpField[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  const fields: FollowUpField[] = [];

  value.forEach((entry, index) => {
    if (!entry || typeof entry !== "object") {
      return;
    }

    const payload = entry as Record<string, unknown>;
    const label =
      typeof payload.question === "string"
        ? payload.question
        : typeof payload.label === "string"
          ? payload.label
          : undefined;

    if (!label) {
      return;
    }

    const options: FollowUpOption[] = [];
    if (Array.isArray(payload.options)) {
      payload.options.forEach((option) => {
        if (!option || typeof option !== "object") {
          return;
        }
        const optionPayload = option as Record<string, unknown>;
        const optionValue = optionPayload.value ?? optionPayload.label;
        const optionLabel = optionPayload.label ?? optionPayload.value;
        if (optionValue === undefined || optionLabel === undefined) {
          return;
        }
        options.push({
          value: String(optionValue),
          label: String(optionLabel),
        });
      });
    }

    fields.push({
      id: typeof payload.id === "string" ? payload.id : buildFieldId(label, index),
      label,
      type: normalizeFieldType(payload.input_type ?? payload.type),
      required: payload.required === undefined ? undefined : Boolean(payload.required),
      helper_text:
        typeof payload.helper_text === "string"
          ? payload.helper_text
          : typeof payload.description === "string"
            ? payload.description
            : undefined,
      placeholder: typeof payload.placeholder === "string" ? payload.placeholder : undefined,
      options: options.length ? options : undefined,
    });
  });

  return fields;
};

const parseFollowUpForm = (
  rawForm: unknown,
  formId?: string
): FollowUpFormDescriptor | undefined => {
  if (!rawForm || typeof rawForm !== "object") {
    return undefined;
  }
  if (Array.isArray(rawForm)) {
    const fields = parseFollowUpFormFields(rawForm);
    if (!fields.length) {
      return undefined;
    }
    return {
      id: typeof formId === "string" && formId.length ? formId : undefined,
      title: undefined,
      description: null,
      status: "in_progress",
      fields,
    } satisfies FollowUpFormDescriptor;
  }
  const payload = rawForm as Record<string, unknown>;
  const fields = parseFollowUpFormFields(payload.fields);
  if (!fields.length) {
    return undefined;
  }

  const descriptor: FollowUpFormDescriptor = {
    id: typeof formId === "string" && formId.length ? formId : undefined,
    title: typeof payload.title === "string" ? payload.title : undefined,
    description: typeof payload.description === "string" ? payload.description : null,
    status: coerceFormStatus(payload.status) ?? "in_progress",
    submitted_at: typeof payload.submitted_at === "string" ? payload.submitted_at : undefined,
    rejected_at: typeof payload.rejected_at === "string" ? payload.rejected_at : undefined,
    rejection_reason: typeof payload.rejection_reason === "string" ? payload.rejection_reason : undefined,
    fields,
  };

  if (!descriptor.id && typeof payload.id === "string") {
    descriptor.id = payload.id;
  }

  return descriptor;
};

const parseFieldValue = (value: unknown): string | number | string[] | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (Array.isArray(value)) {
    return value.map((entry) => String(entry));
  }
  if (typeof value === "number") {
    return value;
  }
  return String(value);
};

const parseFollowUpFormSubmission = (value: unknown): FollowUpFormSubmissionState | undefined => {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const payload = value as Record<string, unknown>;
  const fields: FollowUpFormSubmissionField[] = [];

  if (Array.isArray(payload.fields)) {
    payload.fields.forEach((entry) => {
      if (!entry || typeof entry !== "object") {
        return;
      }
      const fieldPayload = entry as Record<string, unknown>;
      const id = typeof fieldPayload.id === "string" ? fieldPayload.id : undefined;
      const label = typeof fieldPayload.label === "string" ? fieldPayload.label : undefined;
      if (!id || !label) {
        return;
      }

      const attachments: Array<{ name: string; mime_type?: string; size_bytes?: number }> = [];
      if (Array.isArray(fieldPayload.attachments)) {
        fieldPayload.attachments.forEach((item) => {
          if (!item || typeof item !== "object") {
            return;
          }
          const attachmentPayload = item as Record<string, unknown>;
          const name = typeof attachmentPayload.name === "string" ? attachmentPayload.name : undefined;
          if (!name) {
            return;
          }
          attachments.push({
            name,
            mime_type: typeof attachmentPayload.mime_type === "string" ? attachmentPayload.mime_type : undefined,
            size_bytes: typeof attachmentPayload.size_bytes === "number" ? attachmentPayload.size_bytes : undefined,
          });
        });
      }

      fields.push({
        id,
        label,
        type: normalizeFieldType(fieldPayload.type),
        value: parseFieldValue(fieldPayload.value),
        attachments: attachments.length ? attachments : undefined,
      });
    });
  }

  return {
    replied_to: typeof payload.replied_to === "string" ? payload.replied_to : undefined,
    status: coerceFormStatus(payload.status) ?? (fields.length ? "submitted" : undefined),
    submitted_at: typeof payload.submitted_at === "string" ? payload.submitted_at : undefined,
    fields,
  } satisfies FollowUpFormSubmissionState;
};

const mapMetadata = (metadata: Record<string, unknown>): MessageMetadata => {
  const enriched: MessageMetadata = { ...(metadata as MessageMetadata) };
  const metadataRecord = metadata as Record<string, unknown>;

  const suggestedSource = metadataRecord["suggested_actions"];
  enriched.suggested_actions = coerceStringArray(suggestedSource);
  enriched.follow_up_questions = coerceStringArray(metadata.follow_up_questions);
  enriched.knowledge_hits = parseKnowledgeHits(metadata.knowledge_hits);
  enriched.tool_results = coerceToolResults(metadata.tool_results);
  enriched.needs_more_info = typeof metadata.needs_more_info === "boolean" ? metadata.needs_more_info : undefined;
  enriched.escalate = typeof metadata.escalate === "boolean" ? metadata.escalate : undefined;
  enriched.has_image = typeof metadata.image_attached === "boolean" ? metadata.image_attached : undefined;
  enriched.image_mime_type = typeof metadata.image_mime_type === "string" ? metadata.image_mime_type : undefined;
  enriched.image_file_name = typeof metadata.image_file_name === "string" ? metadata.image_file_name : undefined;
  enriched.image_url = typeof metadata.image_url === "string" ? metadata.image_url : undefined;
  enriched.image_count = typeof metadata.image_count === "number" ? metadata.image_count : undefined;
  enriched.images_b64 = Array.isArray(metadata.images_b64) ? (metadata.images_b64 as string[]) : undefined;
  enriched.attachments = parseAttachments(metadata.attachments);
  enriched.extra =
    typeof metadata.extra === "object" && metadata.extra !== null
      ? (metadata.extra as Record<string, unknown>)
      : undefined;
  const confidenceValue = typeof metadata.confidence === "number" ? metadata.confidence : undefined;
  const extraConfidence =
    enriched.extra && typeof (enriched.extra as Record<string, unknown>).confidence === "number"
      ? ((enriched.extra as Record<string, unknown>).confidence as number)
      : undefined;
  enriched.confidence = confidenceValue ?? extraConfidence;

  const formId = typeof metadata.form_id === "string" ? metadata.form_id : undefined;
  const followUpForm = parseFollowUpForm(metadata.follow_up_form, formId);
  const followUpFormSubmission = parseFollowUpFormSubmission(
    metadata.follow_up_form_submission ?? metadata.follow_up_form_response
  );
  const legacyQuestions = enriched.follow_up_questions;

  let effectiveForm = followUpForm;
  if (!effectiveForm && legacyQuestions?.length) {
    effectiveForm = {
      id: formId,
      title: undefined,
      description: undefined,
      status: "in_progress",
      fields: legacyQuestions.map((question, index) => ({
        id: `legacy-${index}`,
        label: question,
        type: "textarea",
        required: false,
        helper_text: undefined,
        placeholder: undefined,
        options: undefined,
      })),
    } satisfies FollowUpFormDescriptor;
  }

  if (effectiveForm) {
    if (!effectiveForm.id && formId) {
      effectiveForm.id = formId;
    }
    if (followUpFormSubmission) {
      effectiveForm.submission = followUpFormSubmission;
      effectiveForm.status = followUpFormSubmission.status ?? effectiveForm.status ?? "submitted";
      effectiveForm.submitted_at = followUpFormSubmission.submitted_at ?? effectiveForm.submitted_at ?? null;
    }
    enriched.follow_up_form = effectiveForm;
  } else {
    enriched.follow_up_form = undefined;
  }

  enriched.follow_up_form_submission = followUpFormSubmission;
  enriched.form_id = followUpForm?.id ?? formId;
  enriched.follow_up_form_summary =
    typeof metadata.follow_up_form_summary === "string" ? metadata.follow_up_form_summary : undefined;
  enriched.client_hidden = metadata.client_hidden === true ? true : undefined;

  return enriched;
};

const mergeFollowUpSubmissions = (items: ChatMessage[]): ChatMessage[] => {
  const submissionByMessage = new Map<string, FollowUpFormSubmissionState>();

  items.forEach((message) => {
    const submission = message.metadata.follow_up_form_submission;
    if (submission?.replied_to) {
      submissionByMessage.set(submission.replied_to, submission);
    }
  });

  return items.map((message) => {
    if (message.role !== "assistant" || !message.metadata.follow_up_form) {
      return message;
    }

    const existingForm = message.metadata.follow_up_form;
    const submission = submissionByMessage.get(message.id) ?? existingForm.submission;
    if (!submission) {
      return message;
    }

    const mergedForm: FollowUpFormDescriptor = {
      ...existingForm,
      submission,
      status: submission.status ?? existingForm.status ?? "submitted",
      submitted_at: submission.submitted_at ?? existingForm.submitted_at ?? null,
    };

    return {
      ...message,
      metadata: {
        ...message.metadata,
        follow_up_form: mergedForm,
      },
    };
  });
};

const toChatMessage = (message: ApiConversationMessage): ChatMessage => ({
  id: message.id,
  sessionId: message.session_id,
  role: message.role as ChatMessage["role"],
  content: message.content,
  timestamp: message.created_at,
  metadata: mapMetadata(message.message_metadata ?? {})
});

const formatUpdatedLabel = (iso: string) => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return `Updated ${sessionDateFormatter.format(date)}`;
};

const toConversationSession = (
  session: ApiConversationSession,
  title: string
): ConversationSession => ({
  id: session.id,
  status: session.status as ConversationSession["status"],
  createdAt: session.created_at,
  updatedAt: session.updated_at,
  title,
  lastUpdatedLabel: formatUpdatedLabel(session.updated_at),
  endedAt: session.ended_at ?? null,
  feedbackRating: session.feedback_rating ?? null,
});

const deriveSessionTitle = (
  apiSession: ApiConversationSession,
  history: ChatMessage[] | undefined,
  fallbackIndex: number
) => {
  const meaningfulMessage = history?.find((entry) => entry.role === "user" && entry.content.trim().length > 0);
  if (meaningfulMessage) {
    return truncate(meaningfulMessage.content);
  }
  const created = new Date(apiSession.created_at);
  if (!Number.isNaN(created.getTime())) {
    return `Session from ${sessionDateFormatter.format(created)}`;
  }
  return `Session ${fallbackIndex + 1}`;
};

export interface ChatOutletContext {
  sessions: ConversationSession[];
  isLoadingSessions: boolean;
  refreshSessions: () => Promise<void>;
  selectSession: (sessionId: string) => void;
  startNewConversation: () => void;
  messages: ChatMessage[];
  isLoadingMessages: boolean;
  isSending: boolean;
  sendMessage: ({
    message,
    attachments,
    metadata,
    forceSend,
  }: {
    message: string;
    attachments: File[];
    metadata?: Record<string, unknown>;
    forceSend?: boolean;
  }) => Promise<void>;
  canCompose: boolean;
  feedbackSubmitted: boolean;
  submitFeedback?: (rating: number, comment?: string) => Promise<void>;
  activeSessionId: string | null;
  activeSession: ConversationSession | null;
  sessionClosed: boolean;
  navigateToDashboard: () => void;
  loadHistory: (sessionId: string) => Promise<void>;
}

function ChatLayout() {
  const navigate = useNavigate();
  const matchConversation = useMatch("/c/:sessionId");
  const matchConversationRoot = useMatch({ path: "/c", end: true });

  const [sessions, setSessions] = useState<ConversationSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    const sessionId = matchConversation?.params.sessionId;
    if (!sessionId || sessionId === "new") {
      return null;
    }
    return sessionId;
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeSession = useMemo(
    () =>
      activeSessionId
        ? sessions.find((session: ConversationSession) => session.id === activeSessionId) ?? null
        : null,
    [sessions, activeSessionId]
  );

  const sessionClosed =
    !!activeSession && (activeSession.status === "resolved" || activeSession.status === "escalated");
  const canCompose = !sessionClosed;
  const feedbackSubmitted = Boolean(activeSession?.feedbackRating);

  useEffect(() => {
    if (matchConversation?.params.sessionId) {
      const { sessionId } = matchConversation.params;
      if (sessionId && sessionId !== activeSessionId) {
        setActiveSessionId(sessionId === "new" ? null : sessionId);
      }
      return;
    }

    if (matchConversationRoot) {
      if (activeSessionId !== null) {
        setActiveSessionId(null);
      }
      return;
    }

    if (activeSessionId !== null) {
      setActiveSessionId(null);
    }
  }, [activeSessionId, matchConversation, matchConversationRoot]);

  const refreshSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      const apiSessions = await fetchSessions(50);
      const mapped = apiSessions.map((session, index) =>
        toConversationSession(session, deriveSessionTitle(session, undefined, index))
      );
      setSessions(mapped);
      setError(null);
    } catch (err) {
      console.error("Failed to load sessions", err);
      setError("Unable to load conversations. Please try again.");
    } finally {
      setIsLoadingSessions(false);
    }
  }, []);

  const loadHistory = useCallback(
    async (sessionId: string) => {
      setIsLoadingMessages(true);
      try {
        const response: ApiConversationHistoryResponse = await fetchSessionHistory(sessionId, 100);
        const history = response.history.map(toChatMessage);
        const enrichedHistory = mergeFollowUpSubmissions(history);
        setMessages(enrichedHistory);

        setSessions((prevSessions: ConversationSession[]) =>
          prevSessions.map((session, index) =>
            session.id === response.session.id
              ? toConversationSession(
                  response.session,
                  deriveSessionTitle(response.session, enrichedHistory, index)
                )
              : session
          )
        );
        setError(null);
      } catch (err) {
        console.error("Failed to load session history", err);
        setError("Unable to load conversation history.");
      } finally {
        setIsLoadingMessages(false);
      }
    },
    []
  );

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    if (activeSessionId) {
      void loadHistory(activeSessionId);
    } else {
      setMessages([]);
    }
  }, [activeSessionId, loadHistory]);

  const fileToBase64 = async (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result;
        if (typeof result === "string") {
          const base64 = result.split(",")[1] ?? result;
          resolve(base64);
        } else {
          reject(new Error("Unexpected reader result"));
        }
      };
      reader.onerror = () => reject(reader.error || new Error("Failed to read file"));
      reader.readAsDataURL(file);
    });

  const handleSendMessage: ChatOutletContext["sendMessage"] = async ({
    message,
    attachments,
    metadata: extraMetadata,
    forceSend = false,
  }) => {
    const trimmedMessage = message.trim();
    if (!forceSend && !trimmedMessage && attachments.length === 0) {
      return;
    }

    if (!forceSend && sessionClosed) {
      setError("This conversation has ended. Start a new conversation to continue.");
      throw new Error("conversation_closed");
    }

    setError(null);
    setIsSending(true);

    let tempUserId: string | null = null;
    let tempAssistantId: string | null = null;
    let optimisticMetadata: MessageMetadata = {} as MessageMetadata;
    let hideMessage = extraMetadata?.client_hidden === true;

    const createTempId = () => {
      if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
        return crypto.randomUUID();
      }
      return `temp-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    };

    try {
      let images_b64: string[] | undefined;
      let rawMetadata: Record<string, unknown> | undefined = extraMetadata ? { ...extraMetadata } : undefined;

      if (attachments.length) {
        const encoded = await Promise.all(attachments.map((file) => fileToBase64(file)));
        images_b64 = encoded;
        const attachmentMetadata = {
          image_mime_type: attachments[0]?.type,
          image_file_name: attachments[0]?.name,
          attachments: attachments.map((file, index) => ({
            type: "image",
            name: file.name,
            mime_type: file.type,
            base64: encoded[index],
            size_bytes: file.size,
          })),
          attachment_count: attachments.length,
        };
        rawMetadata = rawMetadata ? { ...attachmentMetadata, ...rawMetadata } : attachmentMetadata;
      }

      const typedMetadata = rawMetadata ? mapMetadata(rawMetadata) : ({} as MessageMetadata);
      hideMessage = typedMetadata.client_hidden === true;

      const now = new Date().toISOString();
      const placeholderContent =
        trimmedMessage ||
        (attachments.length
          ? attachments.length === 1
            ? "[image uploaded]"
            : `[${attachments.length} images uploaded]`
          : "");
      tempUserId = `pending-${createTempId()}`;
      tempAssistantId = `${tempUserId}-assistant`;
      optimisticMetadata = typedMetadata;

      setMessages((prev) => {
        const next = [...prev];
        if (!hideMessage) {
          next.push({
            id: tempUserId as string,
            sessionId: activeSessionId ?? (tempUserId as string),
            role: "user",
            content: placeholderContent,
            timestamp: now,
            metadata: optimisticMetadata,
            status: "pending",
          });
        }
        next.push({
          id: tempAssistantId as string,
          sessionId: activeSessionId ?? (tempUserId as string),
          role: "assistant",
          content: "",
          timestamp: now,
          metadata: {} as MessageMetadata,
          status: "pending",
        });
        return next;
      });

      const imageMimeTypes = attachments.length ? attachments.map((file) => file.type || null) : undefined;
      const requestMetadata = rawMetadata
        ? (JSON.parse(JSON.stringify(rawMetadata)) as Record<string, unknown>)
        : undefined;

      const response = await sendAssistantMessage({
        session_id: activeSessionId ?? undefined,
        text: trimmedMessage.length ? trimmedMessage : undefined,
        images_b64,
        image_mime_types: imageMimeTypes,
        metadata: requestMetadata,
      });

      if (tempAssistantId) {
        const assistantMetadataRaw: Record<string, unknown> = {
          suggested_actions: response.answer.suggested_actions,
          extra: response.answer.metadata,
          knowledge_hits: response.knowledge_hits,
        };
        if (typeof response.answer.confidence === "number") {
          assistantMetadataRaw.confidence = response.answer.confidence;
        }
        if (response.answer.follow_up_form) {
          assistantMetadataRaw.follow_up_form = response.answer.follow_up_form;
        }
        if (response.form_id) {
          assistantMetadataRaw.form_id = response.form_id;
        }

        const assistantMetadata = mapMetadata(assistantMetadataRaw);

        setMessages((prev) =>
          prev.map((messageItem) =>
            messageItem.id === tempAssistantId
              ? {
                  ...messageItem,
                  content: response.answer.reply,
                  metadata: assistantMetadata,
                  status: "pending",
                }
              : messageItem
          )
        );
      }

      const resolvedSessionId = response.session_id;
      navigate(`/c/${resolvedSessionId}`);
      setActiveSessionId(resolvedSessionId);
      await refreshSessions();
      await loadHistory(resolvedSessionId);
    } catch (err) {
      console.error("Failed to send message", err);
      const status =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;
      if (status === 403) {
        setError("This conversation has ended. Start a new conversation to continue.");
      } else {
        setError("We couldn’t reach the assistant. Please retry.");
      }
      if (tempUserId) {
        setMessages((prev) => {
          const withoutAssistant = tempAssistantId ? prev.filter((msg) => msg.id !== tempAssistantId) : prev;
          if (hideMessage) {
            return withoutAssistant;
          }
          return withoutAssistant.map((messageItem) =>
            messageItem.id === tempUserId && messageItem.role === "user"
              ? { ...messageItem, status: "failed" }
              : messageItem
          );
        });
      }
      throw err;
    } finally {
      setIsSending(false);
    }
  };

  const handleSelectSession = (sessionId: string) => {
    navigate(`/c/${sessionId}`);
  };

  const handleStartNew = () => {
    setMessages([]);
    setError(null);
    navigate("/c");
  };

  const handleSubmitFeedback = useCallback(
    async (rating: number, comment?: string) => {
      if (!activeSessionId) {
        throw new Error("No active session selected.");
      }
      if (!sessionClosed) {
        throw new Error("Feedback is only available once the session is complete.");
      }

      try {
        await submitSessionFeedback(activeSessionId, { rating, comment: comment ?? null });
        setSessions((prevSessions: ConversationSession[]) =>
          prevSessions.map((session: ConversationSession) =>
            session.id === activeSessionId ? { ...session, feedbackRating: rating } : session
          )
        );
        refreshSessions().catch((refreshError: unknown) => {
          console.error("Failed to refresh sessions after feedback", refreshError);
        });
      } catch (err) {
        console.error("Failed to submit feedback", err);
        throw err;
      }
    },
    [activeSessionId, refreshSessions, sessionClosed]
  );

  const navigateToDashboard = useCallback(() => {
    navigate("/dashboard");
  }, [navigate]);

  const contextValue: ChatOutletContext = {
    sessions,
    isLoadingSessions,
    refreshSessions,
    selectSession: handleSelectSession,
    startNewConversation: handleStartNew,
    messages,
    isLoadingMessages,
    isSending,
    sendMessage: handleSendMessage,
    canCompose,
    feedbackSubmitted,
    submitFeedback: canCompose ? undefined : handleSubmitFeedback,
    activeSessionId,
    activeSession,
    sessionClosed,
    navigateToDashboard,
    loadHistory,
  };

  return (
    <div className="flex min-h-screen flex-col bg-brand-background text-white">
      <Header onToggleSidebar={navigateToDashboard} />
      <NotificationOverlay message={error} tone="error" onClose={() => setError(null)} />

      <div className="flex flex-1 flex-col">
        <Outlet context={contextValue} />
      </div>

      <Footer />
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route element={<ChatLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<ConversationDashboardPage />} />
        <Route path="c" element={<ConversationDetailPage />} />
        <Route path="c/:sessionId" element={<ConversationDetailPage />} />
        <Route path="*" element={<Navigate to="dashboard" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
