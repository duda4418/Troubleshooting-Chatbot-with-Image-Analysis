import { ChangeEvent, FormEvent, useEffect, useState } from "react";

interface FeedbackPromptProps {
  onSubmit?: (rating: number, comment?: string) => Promise<void> | void;
  initialSubmitted?: boolean;
}

const starValues = [1, 2, 3, 4, 5] as const;

const FeedbackPrompt = ({ onSubmit, initialSubmitted = false }: FeedbackPromptProps) => {
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(initialSubmitted);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsSubmitted(initialSubmitted);
    if (!initialSubmitted) {
      setRating(null);
      setComment("");
    }
    setError(null);
  }, [initialSubmitted]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitted) {
      return;
    }
    if (!rating) {
      setError("Select a rating before submitting.");
      return;
    }

    if (!onSubmit) {
      setIsSubmitted(true);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(rating, comment.trim() ? comment.trim() : undefined);
      setIsSubmitted(true);
    } catch (err) {
      console.error("Failed to submit feedback", err);
      setError("We couldn't save your feedback. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="rounded-2xl border border-brand-border/40 bg-brand-surfaceAlt/80 p-6 text-center text-white/90 shadow-card">
        <p className="text-base font-semibold text-white">Thanks for the feedback!</p>
        <p className="mt-2 text-sm text-white/80">You can start a new conversation anytime.</p>
      </div>
    );
  }

  return (
    <form
      className="space-y-5 rounded-2xl border border-brand-border/40 bg-brand-surfaceAlt/80 p-6 text-white/90 shadow-card backdrop-blur-sm"
      onSubmit={handleSubmit}
    >
      <div>
        <p className="text-base font-semibold text-white">Conversation completed</p>
        <p className="mt-1 text-sm text-white/80">How satisfied are you with the help you received?</p>
      </div>

      <div className="flex items-center justify-center gap-2">
        {starValues.map((value) => {
          const selected = rating !== null && value <= rating;
          return (
            <button
              key={value}
              type="button"
              onClick={() => setRating(value)}
              className={`flex h-10 w-10 items-center justify-center rounded-full border text-sm font-semibold transition ${
                selected
                  ? "border-transparent bg-brand-accent text-brand-primary shadow-sm shadow-brand-accent/40"
                  : "border-brand-border/50 bg-brand-surface text-white/70 hover:border-brand-accent/80 hover:text-white"
              }`}
              aria-label={`${value} star${value > 1 ? "s" : ""}`}
            >
              {value}
            </button>
          );
        })}
      </div>

      <label className="block text-white/90">
        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-white/70">
          Additional comments (optional)
        </span>
        <textarea
          value={comment}
          onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setComment(event.target.value)}
          className="w-full rounded-xl border border-brand-border/50 bg-brand-surface px-3 py-2 text-sm text-white outline-none transition placeholder:text-white/50 focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/25"
          rows={3}
          disabled={isSubmitting}
          placeholder="Let us know what worked well or what could improve."
        />
      </label>

      {error ? <p className="text-sm text-brand-accent">{error}</p> : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-full bg-brand-accent px-4 py-2 text-sm font-semibold text-brand-primary transition hover:bg-brand-accentHover disabled:cursor-not-allowed disabled:bg-brand-accent/40"
      >
        {isSubmitting ? "Sending…" : "Submit feedback"}
      </button>
    </form>
  );
};

export default FeedbackPrompt;
