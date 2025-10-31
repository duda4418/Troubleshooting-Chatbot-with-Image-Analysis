import { memo, useCallback, useEffect, useRef, useState } from "react";
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
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const composerWrapperRef = useRef<HTMLDivElement | null>(null);
  const previousComposerHeight = useRef<number | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const initialScrollRef = useRef(true);
  const lastSessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    const currentSession = activeSessionId ?? null;
    if (lastSessionIdRef.current !== currentSession) {
      lastSessionIdRef.current = currentSession;
      initialScrollRef.current = true;
    }
  }, [activeSessionId]);

  useEffect(() => {
    if (!bottomRef.current) {
      return;
    }

    if (initialScrollRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "auto" });
      initialScrollRef.current = false;
      return;
    }

    if (isAtBottom) {
      bottomRef.current.scrollIntoView({ behavior: "auto" });
    }
  }, [messages, isAtBottom]);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      return undefined;
    }
    const sentinel = bottomRef.current;
    if (!sentinel) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry) {
          setIsAtBottom(entry.isIntersecting);
        }
      },
      {
        root: null,
        threshold: 0,
        rootMargin: "0px 0px -120px 0px"
      }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (typeof ResizeObserver === "undefined") {
      return undefined;
    }
    const node = composerWrapperRef.current;
    if (!node) {
      return undefined;
    }

    const handleResize = () => {
      if (!isAtBottom || typeof window === "undefined") {
        previousComposerHeight.current = null;
        return;
      }

      const currentHeight = node.getBoundingClientRect().height;
      if (previousComposerHeight.current === null) {
        previousComposerHeight.current = currentHeight;
        return;
      }

      const delta = currentHeight - previousComposerHeight.current;
      previousComposerHeight.current = currentHeight;

      if (Math.abs(delta) < 1) {
        return;
      }

      window.scrollBy({ top: delta });
    };

    const observer = new ResizeObserver(() => {
      handleResize();
    });

    observer.observe(node);
    handleResize();

    return () => {
      observer.disconnect();
    };
  }, [isAtBottom]);

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
      <ConversationTimeline
        ref={bottomRef}
        messages={messages}
        loading={loading}
        isBusy={isSending}
        onSubmitForm={handleFormSubmit}
        onDismissForm={handleFormDismiss}
      />

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
