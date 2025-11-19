import { useState } from "react";
import type {
  ProblemCategory,
  ProblemCategoryCreate,
  ProblemCategoryUpdate
} from "../../api/catalogue";

interface CategoryFormProps {
  category?: ProblemCategory;
  onSubmit: (data: ProblemCategoryCreate | ProblemCategoryUpdate) => Promise<void>;
  onCancel: () => void;
}

const CategoryForm = ({ category, onSubmit, onCancel }: CategoryFormProps) => {
  const [formData, setFormData] = useState({
    slug: category?.slug || "",
    name: category?.name || "",
    description: category?.description || ""
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(formData);
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
          disabled={!!category}
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none disabled:opacity-50"
          placeholder="e.g., dirty"
        />
        {category && (
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
          placeholder="e.g., Dishes remain dirty"
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
          rows={3}
          className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
          placeholder="Describe the problem category..."
        />
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
          {isSubmitting ? "Saving..." : category ? "Update Category" : "Create Category"}
        </button>
      </div>
    </form>
  );
};

export default CategoryForm;
