import clsx from "clsx";
import { ReactNode } from "react";
import type { ChatMessage } from "../../types";

export type MessageBubbleProps = {
  role: ChatMessage["role"];
  children: ReactNode;
  header?: ReactNode;
  footer?: ReactNode;
  status?: ChatMessage["status"];
};

const ROLE_VARIANTS: Record<ChatMessage["role"], string> = {
  user: "bg-brand-accent text-white",
  assistant: "bg-brand-surfaceAlt/80 text-white",
  system: "bg-brand-surface/80 text-brand-secondary",
  tool: "bg-brand-surface/60 text-brand-secondary"
};

const MessageBubble = ({ role, children, header, footer, status }: MessageBubbleProps) => {
  const alignment = role === "user" ? "items-end" : "items-start";
  const bubbleTone = ROLE_VARIANTS[role];
  const stateTone =
    status === "pending"
      ? "opacity-90"
      : status === "failed"
        ? "ring-1 ring-rose-500/60"
        : undefined;

  return (
    <div className={clsx("flex flex-col gap-2", alignment)}>
      {header ? <div className="px-1 text-xs uppercase tracking-wide text-brand-secondary/60">{header}</div> : null}
      <div
        className={clsx(
          "max-w-2xl rounded-3xl px-5 py-4 text-sm shadow-lg shadow-black/20",
          role === "user" ? "rounded-br-md" : "rounded-bl-md",
          bubbleTone,
          stateTone
        )}
        aria-busy={status === "pending"}
      >
        {children}
      </div>
      {footer ? <div className="px-1 text-[10px] uppercase tracking-wide text-brand-secondary/40">{footer}</div> : null}
    </div>
  );
};

export default MessageBubble;
