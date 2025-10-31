import clsx from "clsx";
import type { ConversationSession } from "../../types";

interface ConversationHeaderProps {
  title: string;
  subtitle: string;
  status?: ConversationSession["status"];
  onStartNew?: () => void;
}

const STATUS_VARIANTS: Record<ConversationSession["status"], { label: string; tone: string }> = {
  in_progress: {
    label: "In Progress",
    tone: "border-brand-accent/50 bg-brand-accent/15 text-white"
  },
  resolved: {
    label: "Resolved",
    tone: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
  },
  escalated: {
    label: "Escalated",
    tone: "border-rose-500/40 bg-rose-500/10 text-rose-200"
  },
  needs_attention: {
    label: "Needs Attention",
    tone: "border-amber-400/40 bg-amber-400/10 text-amber-100"
  }
};

const ConversationHeader = ({ title, subtitle, status, onStartNew }: ConversationHeaderProps) => {
  const statusConfig = status ? STATUS_VARIANTS[status] : undefined;

  return (
    <header className="rounded-3xl border border-brand-border/40 bg-brand-surfaceAlt/80 px-6 py-5 shadow-lg shadow-black/25 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold text-white">{title}</h2>
          <p className="text-sm text-brand-secondary/70">{subtitle}</p>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {statusConfig ? (
            <span
              className={clsx(
                "inline-flex items-center gap-2 rounded-full border px-3 py-1 font-semibold uppercase tracking-wide",
                statusConfig.tone
              )}
            >
              <span className="h-2 w-2 rounded-full bg-current" aria-hidden />
              {statusConfig.label}
            </span>
          ) : null}

          {onStartNew ? (
            <button
              type="button"
              onClick={onStartNew}
              className="rounded-full border border-white/10 px-3 py-1 text-white/70 transition hover:border-brand-accent hover:text-white"
            >
              New session
            </button>
          ) : null}
        </div>
      </div>
    </header>
  );
};

export default ConversationHeader;
