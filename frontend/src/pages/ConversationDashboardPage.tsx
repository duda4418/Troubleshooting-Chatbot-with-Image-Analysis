import { useOutletContext } from "react-router-dom";
import ConversationList from "components/dashboard/ConversationList";
import UsageOverview from "components/dashboard/UsageOverview";
import type { ChatOutletContext } from "../App";

const ConversationDashboardPage = () => {
  const {
    sessions,
    isLoadingSessions,
    refreshSessions,
    selectSession,
    startNewConversation,
  } = useOutletContext<ChatOutletContext>();

  return (
    <div className="mx-auto flex w-full max-w-[1280px] flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-white">Conversation dashboard</h1>
          <p className="text-sm text-white/60">Review recent sessions, feedback, and usage trends.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => {
              void refreshSessions();
            }}
            className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-brand-accent hover:text-brand-accent"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={startNewConversation}
            className="rounded-full bg-brand-accent px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-brand-accent/40 transition hover:bg-brand-accent/90"
          >
            Start new conversation
          </button>
        </div>
      </div>

      <UsageOverview />

      <ConversationList
        sessions={sessions}
        loading={isLoadingSessions}
        onSelectSession={selectSession}
      />
    </div>
  );
};

export default ConversationDashboardPage;
