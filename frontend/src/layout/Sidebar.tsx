import { ArrowPathIcon, ChatBubbleLeftRightIcon, ChevronRightIcon, PlusIcon } from "@heroicons/react/24/outline";
import clsx from "clsx";
import type { ConversationSession } from "../types";

interface SidebarProps {
  sessions: ConversationSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  open: boolean;
  loading?: boolean;
  onStartNew?: () => void;
  onToggleSidebar: () => void;
}

const skeletonItems = Array.from({ length: 4 }, (_, index) => index);

const Sidebar = ({
  sessions,
  activeSessionId,
  onSelectSession,
  open,
  loading = false,
  onStartNew,
  onToggleSidebar
}: SidebarProps) => {
  return (
    <>
      <aside
        className={clsx(
          "fixed inset-y-0 right-0 z-40 flex w-full max-w-sm flex-col overflow-hidden border-l border-white/10 bg-brand-surface/95 text-white shadow-2xl shadow-black/40 backdrop-blur transition-transform duration-300",
          open ? "pointer-events-auto translate-x-0" : "pointer-events-none translate-x-[110%]",
          "lg:right-8 lg:top-[6.25rem] lg:bottom-8 lg:w-[22rem] lg:max-w-[22rem] lg:rounded-3xl lg:border lg:border-white/10 lg:bg-brand-surface/85 lg:shadow-2xl lg:shadow-black/30 lg:backdrop-blur-xl"
        )}
      >
        <div className="flex items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-white">Conversations</h2>
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/80">{sessions.length}</span>
          </div>
          <button
            type="button"
            onClick={onToggleSidebar}
            className="hidden h-9 w-9 items-center justify-center rounded-full border border-white/10 text-brand-secondary transition hover:border-brand-accent hover:text-brand-accent lg:flex"
            aria-label="Collapse conversation list"
          >
            <ChevronRightIcon className="h-4 w-4" />
          </button>
        </div>

        {onStartNew ? (
          <button
            type="button"
            onClick={onStartNew}
            className="mx-5 mb-3 inline-flex items-center gap-2 rounded-full border border-brand-accent/50 px-4 py-2 text-xs font-semibold text-brand-accent transition hover:border-brand-accent hover:bg-brand-accent/10 hover:text-white"
          >
            <PlusIcon className="h-4 w-4" /> New session
          </button>
        ) : null}

        <nav className="flex-1 overflow-y-auto px-5 pb-6 scrollbar-thin">
          <ul className="space-y-2">
            {loading
              ? skeletonItems.map((item) => (
                  <li key={`skeleton-${item}`} className="h-14 animate-pulse rounded-xl bg-white/5" />
                ))
              : null}

            {!loading && sessions.length === 0 ? (
              <li className="rounded-xl bg-white/5 p-6 text-center text-sm text-brand-secondary/70">
                <ChatBubbleLeftRightIcon className="mx-auto h-8 w-8 text-brand-secondary/50" />
                <p className="mt-3 font-medium text-white/80">No sessions yet</p>
                <p className="mt-1 text-xs">Send a new message to begin troubleshooting.</p>
              </li>
            ) : null}

            {!loading
              ? sessions.map((session) => {
                  const isActive = session.id === activeSessionId;
                  return (
                    <li key={session.id}>
                      <button
                        type="button"
                        onClick={() => onSelectSession(session.id)}
                        className={clsx(
                          "w-full rounded-xl px-4 py-3 text-left transition",
                          isActive
                            ? "bg-brand-accent/15 text-white"
                            : "text-brand-secondary/80 hover:bg-white/5"
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-white/90">{session.title}</span>
                          <span className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-brand-secondary/60">
                            <ArrowPathIcon className="h-3 w-3" />
                            {session.status.replace("_", " ")}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-brand-secondary/60">{session.lastUpdatedLabel}</p>
                      </button>
                    </li>
                  );
                })
              : null}
          </ul>
        </nav>
      </aside>

      {/* Sidebar toggle now handled by header button; no floating reopen control needed. */}
    </>
  );
};

export default Sidebar;
