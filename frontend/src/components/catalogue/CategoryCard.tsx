import type { ProblemCategory } from "../../api/catalogue";

interface CategoryCardProps {
  category: ProblemCategory;
  causesCount: number;
  onEdit: () => void;
  onDelete: () => void;
  onClick: () => void;
}

const CategoryCard = ({ category, causesCount, onEdit, onDelete, onClick }: CategoryCardProps) => {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-brand-border bg-brand-surface p-5 transition hover:border-brand-accent/50">
      {/* Card content - clickable area */}
      <div onClick={onClick} className="cursor-pointer">
        <div className="mb-2 flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white group-hover:text-brand-accent transition">
              {category.name}
            </h3>
            <p className="mt-1 text-xs font-mono text-white/50">slug: {category.slug}</p>
          </div>
        </div>

        {category.description && (
          <p className="mt-2 text-sm text-white/70 line-clamp-2">{category.description}</p>
        )}

        <div className="mt-3 flex items-center gap-3 text-xs text-white/50">
          <span className="flex items-center gap-1">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            {causesCount} {causesCount === 1 ? "cause" : "causes"}
          </span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="mt-4 flex gap-2 border-t border-white/5 pt-3">
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

export default CategoryCard;
