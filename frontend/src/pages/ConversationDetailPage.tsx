import clsx from "clsx";
import { useOutletContext } from "react-router-dom";
import ConversationView from "components/ConversationView";
import type { ChatOutletContext } from "../App";

const STATUS_LABELS: Record<string, string> = {
  in_progress: "In progress",
  resolved: "Resolved",
  escalated: "Escalated",
  needs_attention: "Needs attention",
};

const STATUS_COLORS: Record<string, string> = {
  in_progress: "bg-brand-surfaceAlt/80 text-brand-secondary",
  resolved: "bg-emerald-400/15 text-emerald-300",
  escalated: "bg-amber-400/15 text-amber-300",
  needs_attention: "bg-rose-500/15 text-rose-300",
};

const ConversationDetailPage = () => {
  const {
    activeSession,
    activeSessionId,
    messages,
    isLoadingMessages,
    isSending,
    sendMessage,
    canCompose,
    feedbackSubmitted,
    submitFeedback,
    navigateToDashboard,
  } = useOutletContext<ChatOutletContext>();

  const statusBadge = activeSession
    ? STATUS_COLORS[activeSession.status] ?? "bg-white/10 text-white/70"
    : "bg-white/10 text-white/70";
  const statusLabel = activeSession
    ? STATUS_LABELS[activeSession.status] ?? activeSession.status
    : "Draft";

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 pb-12 pt-4 sm:px-6 lg:px-10">
      <div className="sticky top-[72px] z-20 -mx-4 flex flex-col gap-3 px-4 pb-3 pt-2 sm:mx-0 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={navigateToDashboard}
            className="-ml-4 inline-flex items-center gap-2 py-1 text-[0.95rem] font-semibold text-brand-accent transition hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-accent"
          >
            <span aria-hidden className="flex h-4 w-4 items-center justify-center">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </span>
            Back
          </button>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 min-h-0">
        <ConversationView
          messages={messages}
          loading={isLoadingMessages}
          isSending={isSending}
          activeSessionId={activeSessionId}
          onSendMessage={sendMessage}
          canCompose={canCompose}
          feedbackSubmitted={feedbackSubmitted}
          onSubmitFeedback={submitFeedback}
        />
      </div>
    </div>
  );
};

export default ConversationDetailPage;
