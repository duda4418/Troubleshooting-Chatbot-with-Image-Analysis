import type { ProblemSolution } from "../../api/catalogue";

interface SolutionCardProps {
  solution: ProblemSolution;
  onEdit: () => void;
  onDelete: () => void;
}

const SolutionCard = ({ solution, onEdit, onDelete }: SolutionCardProps) => {
  return (
    <div className="group overflow-hidden rounded-xl border border-brand-border bg-brand-surface p-4 transition hover:border-brand-accent/50">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h5 className="font-semibold text-white group-hover:text-brand-accent transition">
              {solution.title}
            </h5>
            {solution.requires_escalation && (
              <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-xs font-medium text-red-400">
                Escalation Required
              </span>
            )}
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-medium text-white/60">
              Step {solution.step_order}
            </span>
          </div>
          <p className="mt-0.5 text-xs font-mono text-white/50">slug: {solution.slug}</p>
        </div>
      </div>

      {solution.summary && (
        <p className="mt-2 text-sm text-white/70 line-clamp-2">{solution.summary}</p>
      )}

      <div className="mt-2">
        <p className="mb-1 text-xs font-medium text-white/60">Instructions:</p>
        <p className="text-sm text-white/70 line-clamp-3">{solution.instructions}</p>
      </div>

      {/* Action buttons */}
      <div className="mt-3 flex gap-2 border-t border-white/5 pt-2">
        <button
          onClick={onEdit}
          className="flex-1 rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium text-white transition hover:border-brand-accent hover:text-brand-accent"
        >
          Edit
        </button>
        <button
          onClick={onDelete}
          className="flex-1 rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium text-white transition hover:border-red-500 hover:text-red-500"
        >
          Delete
        </button>
      </div>
    </div>
  );
};

export default SolutionCard;
