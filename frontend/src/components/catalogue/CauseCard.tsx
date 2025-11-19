import type { ProblemCause } from "../../api/catalogue";

interface CauseCardProps {
  cause: ProblemCause;
  solutionsCount: number;
  onEdit: () => void;
  onDelete: () => void;
  onClick: () => void;
}

const CauseCard = ({ cause, solutionsCount, onEdit, onDelete, onClick }: CauseCardProps) => {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-brand-border bg-brand-surface p-4 transition hover:border-brand-accent/50">
      {/* Card content - clickable area */}
      <div onClick={onClick} className="cursor-pointer">
        <div className="mb-2 flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-white group-hover:text-brand-accent transition">
                {cause.name}
              </h4>
              <span className="rounded-full bg-brand-accent/20 px-2 py-0.5 text-xs font-medium text-brand-accent">
                Priority: {cause.default_priority}
              </span>
            </div>
            <p className="mt-0.5 text-xs font-mono text-white/50">slug: {cause.slug}</p>
          </div>
        </div>

        {cause.description && (
          <p className="mt-2 text-sm text-white/70 line-clamp-2">{cause.description}</p>
        )}

        {cause.detection_hints.length > 0 && (
          <div className="mt-2">
            <p className="mb-1 text-xs font-medium text-white/60">Detection Hints:</p>
            <div className="flex flex-wrap gap-1">
              {cause.detection_hints.slice(0, 3).map((hint, idx) => (
                <span
                  key={idx}
                  className="rounded-md bg-white/5 px-2 py-0.5 text-xs text-white/60"
                >
                  {hint}
                </span>
              ))}
              {cause.detection_hints.length > 3 && (
                <span className="rounded-md bg-white/5 px-2 py-0.5 text-xs text-white/60">
                  +{cause.detection_hints.length - 3} more
                </span>
              )}
            </div>
          </div>
        )}

        <div className="mt-3 flex items-center gap-3 text-xs text-white/50">
          <span className="flex items-center gap-1">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {solutionsCount} {solutionsCount === 1 ? "solution" : "solutions"}
          </span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="mt-3 flex gap-2 border-t border-white/5 pt-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="flex-1 rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium text-white transition hover:border-brand-accent hover:text-brand-accent"
        >
          Edit
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="flex-1 rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium text-white transition hover:border-red-500 hover:text-red-500"
        >
          Delete
        </button>
      </div>
    </div>
  );
};

export default CauseCard;
