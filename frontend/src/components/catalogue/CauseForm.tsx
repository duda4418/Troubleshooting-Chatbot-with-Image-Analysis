import { useState } from "react";
import type { ProblemCause, ProblemCauseCreate, ProblemCauseUpdate } from "../../api/catalogue";

interface CauseFormProps {
  cause?: ProblemCause;
  categoryId: string;
  onSubmit: (data: ProblemCauseCreate | ProblemCauseUpdate) => Promise<void>;
  onCancel: () => void;
}

const CauseForm = ({ cause, categoryId, onSubmit, onCancel }: CauseFormProps) => {
  const [formData, setFormData] = useState({
    slug: cause?.slug || "",
    name: cause?.name || "",
    description: cause?.description || "",
    default_priority: cause?.default_priority ?? 0,
    detection_hints: cause?.detection_hints?.join("\n") || ""
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        ...formData,
        detection_hints: formData.detection_hints
          .split("\n")
          .map((h) => h.trim())
          .filter((h) => h.length > 0),
        ...(cause ? {} : { category_id: categoryId })
      };
      await onSubmit(payload as ProblemCauseCreate | ProblemCauseUpdate);
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
          disabled={!!cause}
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none disabled:opacity-50"
          placeholder="e.g., low_wash_temperature"
        />
        {cause && (
          <p className="mt-1 text-xs text-white/50">Slug cannot be changed after creation</p>
        )}
      </div>

      <div>
        <label htmlFor="name" className="mb-1 block text-sm font-medium text-white/80">
          Name <span className="text-brand-accent">*</span>
        </label>
        <input
          type="text"
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
          placeholder="e.g., Low wash temperature"
        />
      </div>

      <div>
        <label htmlFor="description" className="mb-1 block text-sm font-medium text-white/80">
          Description
        </label>
        <textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          rows={2}
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
          placeholder="Describe the cause..."
        />
      </div>

      <div>
        <label htmlFor="priority" className="mb-1 block text-sm font-medium text-white/80">
          Priority
        </label>
        <input
          type="number"
          id="priority"
          value={formData.default_priority}
          onChange={(e) =>
            setFormData({ ...formData, default_priority: parseInt(e.target.value) || 0 })
          }
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
          placeholder="0"
        />
        <p className="mt-1 text-xs text-white/50">Lower numbers = higher priority</p>
      </div>

      <div>
        <label htmlFor="hints" className="mb-1 block text-sm font-medium text-white/80">
          Detection Hints
        </label>
        <textarea
          id="hints"
          value={formData.detection_hints}
          onChange={(e) => setFormData({ ...formData, detection_hints: e.target.value })}
          rows={3}
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
          placeholder="Enter one hint per line..."
        />
        <p className="mt-1 text-xs text-white/50">One hint per line</p>
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
          {isSubmitting ? "Saving..." : cause ? "Update Cause" : "Create Cause"}
        </button>
      </div>
    </form>
  );
};

export default CauseForm;
