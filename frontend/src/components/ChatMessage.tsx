import { memo, useMemo } from "react";
import clsx from "clsx";
import MessageBubble from "./messages/MessageBubble";
import MessageMarkdown from "./messages/MessageMarkdown";
import MessageAttachmentGrid from "./messages/MessageAttachmentGrid";
import MessageActionList from "./messages/MessageActionList";
import MessageToolResults from "./messages/MessageToolResults";
import TypingIndicator from "./messages/TypingIndicator";
import { FollowUpForm } from "./followup-form";
import type { FollowUpFormSubmission } from "./followup-form";
import type {
  ChatMessage,
  FollowUpFormDescriptor,
  MessageMetadata,
} from "../types";

interface ChatMessageProps {
  message: ChatMessage;
  isBusy?: boolean;
  onSubmitForm?: (message: ChatMessage, form: FollowUpFormDescriptor, submission: FollowUpFormSubmission) => void;
  onDismissForm?: (message: ChatMessage, form: FollowUpFormDescriptor) => void;
}

const roleLabels: Record<ChatMessage["role"], string> = {
  user: "You",
  assistant: "AI Assistant",
  system: "System Message",
  tool: "Diagnostics Runner"
};

const normalizeAttachments = (metadata: MessageMetadata | undefined) => {
  if (!metadata) {
    return undefined;
  }

  const attachments = Array.isArray(metadata.attachments) ? [...metadata.attachments] : [];

  if (!attachments.length && metadata.image_url) {
    attachments.push({
      type: "image",
      name: metadata.image_file_name,
      url: metadata.image_url
    });
  }

  return attachments.length ? attachments : undefined;
};

const ChatMessageCard = ({ message, isBusy = false, onSubmitForm, onDismissForm }: ChatMessageProps) => {
  if (message.role === "assistant" && message.metadata?.client_hidden) {
    return null;
  }
  const formattedTime = useMemo(() => {
    const date = new Date(message.timestamp);
    if (Number.isNaN(date.getTime())) {
      return "";
    }

    return new Intl.DateTimeFormat("en", {
      hour: "2-digit",
      minute: "2-digit"
    }).format(date);
  }, [message.timestamp]);

  const attachments = useMemo(() => normalizeAttachments(message.metadata), [message.metadata]);
  const followUpForm = useMemo(() => message.metadata?.follow_up_form, [message.metadata]);
  const followUpStatus = followUpForm?.status ?? "in_progress";
  const shouldRenderFollowUp =
    message.role === "assistant" &&
    followUpForm?.fields?.length &&
    followUpStatus === "in_progress" &&
    typeof onSubmitForm === "function";
  const confidenceLabel = useMemo(() => {
    if (message.role !== "assistant") {
      return undefined;
    }
    const confidence = message.metadata?.confidence;
    if (typeof confidence !== "number") {
      return undefined;
    }
    const pct = Math.round(confidence * 100);
    return `Confidence: ${pct}%`;
  }, [message.metadata, message.role]);
  const isAssistantPending = message.role === "assistant" && message.status === "pending";
  const footerText =
    message.status === "pending"
      ? message.role === "user"
        ? "Sending…"
        : "Assistant is thinking…"
      : message.status === "failed"
        ? "Message failed to send"
        : undefined;

  const alignment = message.role === "user" ? "justify-end" : "justify-start";
  
  // Check if message has text or images
  const hasText = message.content && message.content.trim().length > 0;
  const hasImages = attachments && attachments.length > 0;
  const isImageOnly = hasImages && !hasText && message.role === "user";

  const header = (
    <div className="flex items-center gap-2 text-xs uppercase tracking-wide">
      <span className="font-semibold text-white/80">{roleLabels[message.role]}</span>
      {formattedTime ? <time className="text-white/50">{formattedTime}</time> : null}
    </div>
  );

  return (
    <div className={clsx("flex", alignment)}>
      {/* Image-only messages: display images outside bubble */}
      {isImageOnly ? (
        <div className={clsx("flex flex-col gap-2", message.role === "user" ? "items-end" : "items-start")}>
          {header}
          <div className="max-w-sm">
            <MessageAttachmentGrid attachments={attachments} standalone />
          </div>
          {footerText ? (
            <div className="px-1 text-[10px] uppercase tracking-wide text-brand-secondary/40">{footerText}</div>
          ) : null}
        </div>
      ) : (
        /* Regular messages: images above bubble, text in bubble */
        <div className={clsx("flex flex-col gap-2", message.role === "user" ? "items-end" : "items-start")}>
          {header}
          
          {/* Show images above bubble if present */}
          {hasImages ? (
            <div className="max-w-sm">
              <MessageAttachmentGrid attachments={attachments} standalone />
            </div>
          ) : null}
          
          {/* Text bubble */}
          <MessageBubble role={message.role} status={message.status} footer={footerText}>
            {isAssistantPending ? <TypingIndicator /> : hasText ? <MessageMarkdown content={message.content} /> : null}

            {message.metadata?.suggested_actions?.length ? (
              <MessageActionList suggestedActions={message.metadata.suggested_actions} />
            ) : null}

            {message.metadata?.tool_results?.length ? (
              <MessageToolResults results={message.metadata.tool_results} />
            ) : null}

            {confidenceLabel ? (
              <div className="mt-3 text-xs font-medium uppercase tracking-wide text-white/50">{confidenceLabel}</div>
            ) : null}

            {shouldRenderFollowUp ? (
              <FollowUpForm
                form={followUpForm}
                disabled={isBusy || isAssistantPending}
                onSubmit={(submission) => onSubmitForm(message, followUpForm, submission)}
                onDismiss={onDismissForm ? () => onDismissForm(message, followUpForm) : undefined}
              />
            ) : null}
          </MessageBubble>
        </div>
      )}
    </div>
  );
};

export default memo(ChatMessageCard);
