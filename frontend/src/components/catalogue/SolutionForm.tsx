import { useState } from "react";
import type {
  ProblemSolution,
  ProblemSolutionCreate,
  ProblemSolutionUpdate
} from "../../api/catalogue";

interface SolutionFormProps {
  solution?: ProblemSolution;
  causeId: string;
  onSubmit: (data: ProblemSolutionCreate | ProblemSolutionUpdate) => Promise<void>;
  onCancel: () => void;
}

const SolutionForm = ({ solution, causeId, onSubmit, onCancel }: SolutionFormProps) => {
  const [formData, setFormData] = useState({
    slug: solution?.slug || "",
    title: solution?.title || "",
    summary: solution?.summary || "",
    instructions: solution?.instructions || "",
    step_order: solution?.step_order ?? 0,
    requires_escalation: solution?.requires_escalation ?? false
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        ...formData,
        ...(solution ? {} : { cause_id: causeId })
      };
      await onSubmit(payload as ProblemSolutionCreate | ProblemSolutionUpdate);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="slug" className="mb-1 block text-sm font-medium text-white/80">
          Slug <span className="text-brand-accent">*</span>
        </label>
        <input
          type="text"
          id="slug"
          value={formData.slug}
          onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
          required
          disabled={!!solution}
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none disabled:opacity-50"
          placeholder="e.g., raise_wash_temperature"
        />
        {solution && (
          <p className="mt-1 text-xs text-white/50">Slug cannot be changed after creation</p>
        )}
      </div>

      <div>
        <label htmlFor="title" className="mb-1 block text-sm font-medium text-white/80">
          Title <span className="text-brand-accent">*</span>
        </label>
        <input
          type="text"
          id="title"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          required
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
          placeholder="e.g., Raise the main wash temperature"
        />
      </div>

      <div>
        <label htmlFor="summary" className="mb-1 block text-sm font-medium text-white/80">
          Summary
        </label>
        <textarea
          id="summary"
          value={formData.summary}
          onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
          rows={2}
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
          placeholder="Brief summary of the solution..."
        />
      </div>

      <div>
        <label htmlFor="instructions" className="mb-1 block text-sm font-medium text-white/80">
          Instructions <span className="text-brand-accent">*</span>
        </label>
        <textarea
          id="instructions"
          value={formData.instructions}
          onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
          required
          rows={5}
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
          placeholder="Detailed step-by-step instructions..."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="step_order" className="mb-1 block text-sm font-medium text-white/80">
            Step Order
          </label>
          <input
            type="number"
            id="step_order"
            value={formData.step_order}
            onChange={(e) =>
              setFormData({ ...formData, step_order: parseInt(e.target.value) || 0 })
            }
            className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
            placeholder="0"
          />
        </div>

        <div className="flex items-end">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={formData.requires_escalation}
              onChange={(e) =>
                setFormData({ ...formData, requires_escalation: e.target.checked })
              }
              className="h-4 w-4 cursor-pointer rounded border-brand-border bg-brand-surface text-brand-accent focus:ring-2 focus:ring-brand-accent focus:ring-offset-0"
            />
            <span className="text-sm font-medium text-white/80">Requires Escalation</span>
          </label>
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="rounded-lg border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-white/30 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-lg bg-brand-accent px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-brand-accent/40 transition hover:bg-brand-accentHover disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : solution ? "Update Solution" : "Create Solution"}
        </button>
      </div>
    </form>
  );
};

export default SolutionForm;
