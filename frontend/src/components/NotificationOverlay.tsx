import clsx from "clsx";
import type { ReactNode } from "react";

export type NotificationTone = "info" | "success" | "warning" | "error";

interface NotificationOverlayProps {
  message: ReactNode;
  tone?: NotificationTone;
  onClose?: () => void;
}

const toneStyles: Record<NotificationTone, string> = {
  info: "border-sky-400/60 bg-sky-500/15 text-sky-100",
  success: "border-emerald-400/60 bg-emerald-500/15 text-emerald-100",
  warning: "border-amber-400/60 bg-amber-500/10 text-amber-100",
  error: "border-rose-500/60 bg-rose-600/10 text-rose-100"
};

const NotificationOverlay = ({ message, tone = "info", onClose }: NotificationOverlayProps) => {
  if (!message) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-40 flex justify-center px-4">
      <div
        className={clsx(
          "pointer-events-auto flex max-w-2xl items-start gap-3 rounded-2xl border px-5 py-4 text-sm shadow-lg shadow-black/30 backdrop-blur",
          toneStyles[tone]
        )}
      >
        <div className="flex-1 leading-relaxed">{message}</div>
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-white/20 px-3 py-1 text-xs uppercase tracking-wide text-white/80 transition hover:border-white/40 hover:text-white"
          >
            Dismiss
          </button>
        ) : null}
      </div>
    </div>
  );
};

export default NotificationOverlay;
