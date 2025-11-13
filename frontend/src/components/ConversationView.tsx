import { memo, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import ChatComposer from "./ChatComposer";
import ConversationTimeline from "./conversation/ConversationTimeline";
import type { FollowUpFormSubmission } from "./followup-form";
import type { ChatMessage, FollowUpFormDescriptor } from "../types";
import FeedbackPrompt from "./feedback/FeedbackPrompt";

interface ConversationViewProps {
  messages: ChatMessage[];
  onSendMessage: (payload: {
    message: string;
    attachments: File[];
    metadata?: Record<string, unknown>;
    forceSend?: boolean;
  }) => Promise<void> | void;
  isSending?: boolean;
  loading?: boolean;
  activeSessionId?: string | null;
  canCompose?: boolean;
  onSubmitFeedback?: (rating: number, comment?: string) => Promise<void> | void;
  feedbackSubmitted?: boolean;
}

const ConversationView = ({
  messages,
  onSendMessage,
  isSending = false,
  loading = false,
  activeSessionId = null,
  canCompose = true,
  onSubmitFeedback,
  feedbackSubmitted = false,
}: ConversationViewProps) => {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const composerWrapperRef = useRef<HTMLDivElement | null>(null);
  const bottomMarkerRef = useRef<HTMLDivElement | null>(null);
  const lastSessionIdRef = useRef<string | null>(null);
  const initialScrollRef = useRef(true);
  const autoScrollRef = useRef(true);
  const lastSessionForMessagesRef = useRef<string | null>(activeSessionId ?? null);
  const [composerHeight, setComposerHeight] = useState(0);
  const [renderedMessages, setRenderedMessages] = useState<ChatMessage[]>(messages);
  const prevMessageCountRef = useRef(renderedMessages.length);
  const prevLastMessageRef = useRef<ChatMessage | undefined>(
    renderedMessages.length ? renderedMessages[renderedMessages.length - 1] : undefined
  );

  useEffect(() => {
    const marker = bottomMarkerRef.current;
    if (!marker) {
      return;
    }

    const margin = Math.max(composerHeight + 16, 64);
    marker.style.scrollMarginBottom = `${margin}px`;
  }, [composerHeight]);

  useEffect(() => {
    const currentSession = activeSessionId ?? null;
    if (lastSessionIdRef.current !== currentSession) {
      lastSessionIdRef.current = currentSession;
      initialScrollRef.current = true;
      autoScrollRef.current = true;
      lastSessionForMessagesRef.current = currentSession;
      setRenderedMessages([]);
      prevMessageCountRef.current = 0;
      prevLastMessageRef.current = undefined;
      return;
    }
    lastSessionForMessagesRef.current = currentSession;
  }, [activeSessionId, messages]);

  useEffect(() => {
    const targetSession = activeSessionId ?? null;
    const matchesCurrentSession =
      targetSession === null || messages.every((message) => message.sessionId === targetSession);

    if (!matchesCurrentSession) {
      return;
    }

    setRenderedMessages((prev) => {
      if (lastSessionForMessagesRef.current !== targetSession) {
        return messages;
      }
      return mergeMessageLists(prev, messages);
    });
  }, [messages, activeSessionId]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const container = scrollContainerRef.current;
    const marker = bottomMarkerRef.current;
    if (!container) {
      return;
    }

    if (marker) {
      requestAnimationFrame(() => {
        marker.scrollIntoView({ behavior, block: "end" });
      });
      return;
    }

    const runScroll = () => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior,
      });
    };

    if (behavior === "smooth") {
      requestAnimationFrame(runScroll);
      return;
    }

    requestAnimationFrame(() => {
      runScroll();
      requestAnimationFrame(runScroll);
    });
  }, []);

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }

    const threshold = 80;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    autoScrollRef.current = distanceFromBottom <= threshold;
  }, []);

  useLayoutEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }

    const prevCount = prevMessageCountRef.current;
    const nextCount = renderedMessages.length;
    const previousLast = prevLastMessageRef.current;
    const nextLast = nextCount ? renderedMessages[nextCount - 1] : undefined;

    const appended = nextCount > prevCount;
    const lastChanged =
      nextLast && previousLast
        ? !areMessagesEqual(nextLast, previousLast)
        : nextLast !== previousLast;

    prevMessageCountRef.current = nextCount;
    prevLastMessageRef.current = nextLast;

    if (initialScrollRef.current) {
      initialScrollRef.current = false;
      scrollToBottom("auto");
      return;
    }

    if ((appended || lastChanged) && autoScrollRef.current) {
      const behavior = appended && nextCount - prevCount > 1 ? "auto" : "smooth";
      scrollToBottom(behavior);
    }
  }, [renderedMessages, scrollToBottom]);

  useEffect(() => {
    handleScroll();
  }, [handleScroll, renderedMessages.length]);

  const wasLoadingRef = useRef(loading);

  useEffect(() => {
    if (wasLoadingRef.current && !loading) {
      autoScrollRef.current = true;
      initialScrollRef.current = false;
      scrollToBottom("auto");
    }
    wasLoadingRef.current = loading;
  }, [loading, scrollToBottom]);

  useEffect(() => {
    const node = composerWrapperRef.current;
    if (!node) {
      setComposerHeight(0);
      return;
    }

    const updateHeight = () => {
      setComposerHeight(node.getBoundingClientRect().height);
      handleScroll();
    };

    updateHeight();

    if (typeof ResizeObserver === "undefined") {
      return undefined;
    }

    const observer = new ResizeObserver(() => {
      updateHeight();
    });

    observer.observe(node);

    return () => {
      observer.disconnect();
    };
  }, [canCompose, activeSessionId, handleScroll]);

  const handleSend = useCallback(
    async (payload: {
      message: string;
      attachments: File[];
      metadata?: Record<string, unknown>;
      forceSend?: boolean;
    }) => {
      await onSendMessage(payload);
    },
    [onSendMessage]
  );

  const handleFormSubmit = useCallback(
    async (
      message: ChatMessage,
      form: FollowUpFormDescriptor,
      submission: FollowUpFormSubmission
    ) => {
      if (!canCompose) {
        return;
      }
      const fieldResponses = buildFieldResponses(submission, form);
      const metadata = {
        client_hidden: true,
        form_id: submission.formId ?? form.id,
        follow_up_form_response: {
          replied_to: message.id,
          status: "submitted",
          submitted_at: new Date().toISOString(),
          fields: fieldResponses,
        },
      } as Record<string, unknown>;

      await onSendMessage({
        message: "",
        attachments: submission.attachments,
        metadata,
        forceSend: true,
      });
    },
    [onSendMessage, canCompose]
  );

  const handleFormDismiss = useCallback(
    async (message: ChatMessage, form: FollowUpFormDescriptor) => {
      if (!canCompose) {
        return;
      }
      const metadata = {
        client_hidden: true,
        form_id: form.id,
        follow_up_form_response: {
          replied_to: message.id,
          status: "dismissed",
          submitted_at: new Date().toISOString(),
          fields: [],
        },
      } as Record<string, unknown>;

      await onSendMessage({
        message: "",
        attachments: [],
        metadata,
        forceSend: true,
      });
    },
    [onSendMessage, canCompose]
  );

  return (
    <section className="flex h-full flex-col">
      <div className="flex flex-1 flex-col min-h-0">
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto scroll-smooth"
          data-testid="conversation-scroll-area"
        >
          <ConversationTimeline
            messages={renderedMessages}
            loading={loading && renderedMessages.length === 0}
            isBusy={isSending}
            onSubmitForm={handleFormSubmit}
            onDismissForm={handleFormDismiss}
            bottomPadding={composerHeight + 24}
            bottomRef={bottomMarkerRef}
          />
        </div>
      </div>

      <div
        className="sticky bottom-1 z-30 mt-auto bg-gradient-to-t from-brand-background via-brand-background/95 to-transparent px-4 pb-2 pt-3 sm:bottom-1 sm:px-6 lg:bottom-2 lg:px-8"
        style={{ paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 0.35rem)" }}
      >
        <div
          key={activeSessionId ?? "new-session"}
          ref={composerWrapperRef}
          className="mx-auto w-full max-w-3xl"
        >
          {canCompose ? (
            <ChatComposer
              disabled={isSending || loading}
              onSend={handleSend}
              placeholder="Describe the issue you need help with..."
            />
          ) : (
            <FeedbackPrompt onSubmit={onSubmitFeedback} initialSubmitted={feedbackSubmitted} />
          )}
        </div>
      </div>
    </section>
  );
};

export default memo(ConversationView);

const mergeMessageLists = (current: ChatMessage[], incoming: ChatMessage[]): ChatMessage[] => {
  if (current === incoming) {
    return current;
  }

  if (!current.length) {
    return incoming;
  }

  const currentById = new Map(current.map((message) => [message.id, message]));
  let didChange = current.length !== incoming.length;

  const merged = incoming.map((message) => {
    const existing = currentById.get(message.id);
    if (existing && areMessagesEqual(existing, message)) {
      return existing;
    }
    didChange = true;
    return message;
  });

  if (!didChange) {
    return current;
  }

  return merged;
};

const areMessagesEqual = (a: ChatMessage, b: ChatMessage): boolean => {
  if (a === b) {
    return true;
  }

  return (
    a.id === b.id &&
    a.role === b.role &&
    a.content === b.content &&
    a.status === b.status &&
    a.timestamp === b.timestamp &&
    areMetadataEqual(a.metadata, b.metadata)
  );
};

const areMetadataEqual = (a: ChatMessage["metadata"], b: ChatMessage["metadata"]): boolean => {
  if (a === b) {
    return true;
  }

  if (!a || !b) {
    return !a && !b;
  }

  try {
    return JSON.stringify(a) === JSON.stringify(b);
  } catch {
    return false;
  }
};

const buildFieldResponses = (
  submission: FollowUpFormSubmission,
  form: FollowUpFormDescriptor
) =>
  form.fields.map((field) => {
    const rawValue = submission.values[field.id];
    const value = normalizeResponseValue(rawValue);
    const attachments = submission.files[field.id]?.map((file) => ({
      name: file.name,
      mime_type: file.type || undefined,
      size_bytes: file.size,
    }));

    return {
      id: field.id,
      label: field.label,
      type: field.type,
      value,
      attachments: attachments && attachments.length ? attachments : undefined,
    };
  });

const normalizeResponseValue = (
  value: FollowUpFormSubmission["values"][string]
): string | number | string[] | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (Array.isArray(value)) {
    return value.map((entry) => String(entry));
  }
  if (typeof value === "number") {
    return value;
  }
  const text = String(value).trim();
  return text.length ? text : null;
};
