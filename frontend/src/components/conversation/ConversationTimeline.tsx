import { ForwardedRef, forwardRef } from "react";
import clsx from "clsx";
import ChatMessageCard from "../ChatMessage";
import type { FollowUpFormSubmission } from "../followup-form";
import type { ChatMessage, FollowUpFormDescriptor } from "../../types";

interface ConversationTimelineProps {
  messages: ChatMessage[];
  loading?: boolean;
  className?: string;
  isBusy?: boolean;
  onSubmitForm?: (message: ChatMessage, form: FollowUpFormDescriptor, submission: FollowUpFormSubmission) => Promise<void> | void;
  onDismissForm?: (message: ChatMessage, form: FollowUpFormDescriptor) => Promise<void> | void;
}

const ConversationTimeline = forwardRef<HTMLDivElement, ConversationTimelineProps>(
  ({ messages, loading = false, className, isBusy = false, onSubmitForm, onDismissForm }, ref: ForwardedRef<HTMLDivElement>) => {
    const visibleMessages = messages.filter(
      (message) => message.role !== "tool" && message.metadata?.client_hidden !== true
    );

    return (
    <div className={clsx("flex-1 px-6 pb-24 pt-6", className)}>
      <div className="mx-auto flex w-full max-w-3xl flex-col space-y-6">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={`timeline-skeleton-${index}`} className="h-24 animate-pulse rounded-3xl bg-white/5" />
            ))}
          </div>
        ) : null}

        {!loading && visibleMessages.length
          ? visibleMessages.map((message) => (
              <ChatMessageCard
                key={message.id}
                message={message}
                isBusy={isBusy}
                onSubmitForm={onSubmitForm}
                onDismissForm={onDismissForm}
              />
            ))
          : null}

        {!loading && visibleMessages.length === 0 ? (
          <div className="flex min-h-[40vh] items-center justify-center text-center text-sm text-white/40">
            <div className="space-y-2">
              <p className="text-base font-semibold text-white/60">Start a conversation</p>
              <p className="text-white/50">Send a note or add diagnostic photos to begin.</p>
            </div>
          </div>
        ) : null}

        <div ref={ref} />
      </div>
    </div>
    );
  }
);

ConversationTimeline.displayName = "ConversationTimeline";

export default ConversationTimeline;
