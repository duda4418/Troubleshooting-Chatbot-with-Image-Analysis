import clsx from "clsx";

interface TypingIndicatorProps {
  className?: string;
}

const TypingIndicator = ({ className }: TypingIndicatorProps) => (
  <div className={clsx("flex items-center gap-1", className)} aria-label="Assistant is typing">
    <span className="h-2 w-2 animate-bounce rounded-full bg-white/90" style={{ animationDelay: "-0.2s" }} />
    <span className="h-2 w-2 animate-bounce rounded-full bg-white/70" style={{ animationDelay: "-0.1s" }} />
    <span className="h-2 w-2 animate-bounce rounded-full bg-white/60" />
  </div>
);

export default TypingIndicator;
