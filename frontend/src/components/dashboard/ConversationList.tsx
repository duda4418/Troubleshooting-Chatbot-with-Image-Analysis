import { useMemo, useState } from "react";
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import clsx from "clsx";
import type { ConversationSession } from "../../types";

interface ConversationListProps {
  sessions: ConversationSession[];
  loading?: boolean;
  pageSizeOptions?: number[];
  defaultPageSize?: number;
  onSelectSession?: (sessionId: string) => void;
}

const STATUS_LABELS: Record<ConversationSession["status"], string> = {
  in_progress: "In progress",
  resolved: "Resolved",
  escalated: "Escalated",
  needs_attention: "Needs attention",
};

const STATUS_COLORS: Record<ConversationSession["status"], string> = {
  in_progress: "text-brand-secondary",
  resolved: "text-emerald-400",
  escalated: "text-amber-400",
  needs_attention: "text-rose-400",
};

const ConversationList = ({
  sessions,
  loading = false,
  pageSizeOptions = [10, 25, 50],
  defaultPageSize = 10,
  onSelectSession,
}: ConversationListProps) => {
  const normalizedOptions = useMemo(() => {
    const unique = Array.from(new Set([...pageSizeOptions, defaultPageSize])).filter((value) => value > 0);
    return unique.sort((a, b) => a - b);
  }, [pageSizeOptions, defaultPageSize]);

  const [pageSize, setPageSize] = useState(() => normalizedOptions[0] ?? defaultPageSize);
  const [currentPage, setCurrentPage] = useState(0);

  const pageCount = Math.max(1, Math.ceil((sessions.length || 1) / pageSize));

  const pagedSessions = useMemo(() => {
    const start = currentPage * pageSize;
    return sessions.slice(start, start + pageSize);
  }, [sessions, currentPage, pageSize]);

  const handleChangePage = (delta: number) => {
    setCurrentPage((prev) => {
      const next = prev + delta;
      if (next < 0) return 0;
      if (next >= pageCount) return pageCount - 1;
      return next;
    });
  };

  const handleUpdatePageSize = (value: number) => {
    setPageSize(value);
    setCurrentPage(0);
  };

  const handleRowClick = (sessionId: string) => {
    if (onSelectSession) {
      onSelectSession(sessionId);
    }
  };

  const renderBody = () => {
    if (loading) {
      return Array.from({ length: 4 }).map((_, index) => (
        <tr key={`conversation-skeleton-${index}`} className="animate-pulse">
          <td className="px-4 py-3" colSpan={5}>
            <div className="h-10 rounded-xl bg-brand-surfaceAlt/60" />
          </td>
        </tr>
      ));
    }

    if (!sessions.length) {
      return (
        <tr>
          <td className="px-4 py-6 text-center text-sm text-white/60" colSpan={5}>
            No conversations yet. Start a new conversation to populate the list.
          </td>
        </tr>
      );
    }

    return pagedSessions.map((session) => (
      <tr
        key={session.id}
        onClick={() => handleRowClick(session.id)}
        className={clsx(
          "group cursor-pointer transition",
          "hover:bg-white/5 focus-visible:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-accent"
        )}
        tabIndex={0}
      >
        <td className="px-4 py-3 text-sm font-medium text-white/90">{session.title}</td>
        <td className={clsx("px-4 py-3 text-sm", STATUS_COLORS[session.status])}>{STATUS_LABELS[session.status]}</td>
        <td className="px-4 py-3 text-sm text-white/70">{session.createdAt ? new Date(session.createdAt).toLocaleString() : "–"}</td>
        <td className="px-4 py-3 text-sm text-white/70">{session.lastUpdatedLabel}</td>
        <td className="px-4 py-3 text-sm text-white/90 text-right">{session.feedbackRating ? `${session.feedbackRating.toFixed(1)}/5` : "–"}</td>
      </tr>
    ));
  };

  return (
    <section className="flex flex-col rounded-3xl border border-white/10 bg-brand-surface/60 backdrop-blur">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 px-4 py-4 sm:px-6">
        <div>
          <h2 className="text-lg font-semibold">Conversations</h2>
          <p className="text-sm text-white/60">Browse recent sessions and drill into details.</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <label className="flex items-center gap-2 text-white/70">
            Rows per page
            <select
              value={pageSize}
              onChange={(event) => handleUpdatePageSize(Number(event.target.value))}
              className="rounded-lg border border-white/10 bg-brand-surfaceAlt/80 px-3 py-1 text-sm focus:border-brand-accent focus:outline-none focus:ring-2 focus:ring-brand-accent/40"
            >
              {normalizedOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/10 text-left">
          <thead className="text-xs uppercase tracking-wide text-white/60">
            <tr>
              <th className="px-4 py-3 font-semibold">Title</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Created</th>
              <th className="px-4 py-3 font-semibold">Last activity</th>
              <th className="px-4 py-3 font-semibold text-right">Feedback</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-white/80">{renderBody()}</tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between border-t border-white/10 px-4 py-3 text-sm text-white/60 sm:px-6">
        <span>
          Page {pageCount === 0 ? 0 : currentPage + 1} of {pageCount}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleChangePage(-1)}
            disabled={currentPage <= 0}
            className="flex items-center gap-1 rounded-full border border-white/10 px-3 py-1.5 text-white transition enabled:hover:border-brand-accent enabled:hover:text-brand-accent disabled:opacity-40"
          >
            <ChevronLeftIcon className="h-4 w-4" />
            Prev
          </button>
          <button
            type="button"
            onClick={() => handleChangePage(1)}
            disabled={currentPage >= pageCount - 1}
            className="flex items-center gap-1 rounded-full border border-white/10 px-3 py-1.5 text-white transition enabled:hover:border-brand-accent enabled:hover:text-brand-accent disabled:opacity-40"
          >
            Next
            <ChevronRightIcon className="h-4 w-4" />
          </button>
        </div>
      </footer>
    </section>
  );
};

export default ConversationList;
