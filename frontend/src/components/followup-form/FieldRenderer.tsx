import { ChangeEvent } from "react";
import clsx from "clsx";
import type { FollowUpField } from "../../types";
import { DEFAULT_BOOLEAN_OPTIONS, resolveOptions } from "./helpers";
import type { FieldValue } from "./types";

interface FieldRendererProps {
  field: FollowUpField;
  value: FieldValue;
  files: File[];
  disabled?: boolean;
  error?: string;
  onValueChange: (next: FieldValue) => void;
  onFileChange: (next: File[]) => void;
}

const buttonBase =
  "rounded-full border border-white/20 px-3.5 py-1.5 text-xs font-semibold uppercase tracking-wide text-white/80 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-accent/60 disabled:cursor-not-allowed disabled:opacity-60";

const normalizeOptionValue = (value: unknown): string | null => {
  if (value === null || value === undefined) {
    return null;
  }
  const text = String(value).trim().toLowerCase();
  return text.length ? text : null;
};

const FieldRenderer = ({
  field,
  value,
  files,
  disabled = false,
  error,
  onValueChange,
  onFileChange
}: FieldRendererProps) => {
  const options = resolveOptions(field);

  const handleTextChange = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onValueChange(event.target.value);
  };

  const handleNumberChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextValue = event.target.value;
    if (nextValue.trim().length === 0) {
      onValueChange(null);
      return;
    }
    const parsed = Number(nextValue);
    onValueChange(Number.isNaN(parsed) ? null : parsed);
  };

  const handleSingleSelect = (optionValue: string) => {
    onValueChange(optionValue);
  };

  const handleMultiSelect = (optionValue: string) => {
    const next = new Set<string>(Array.isArray(value) ? value.map((entry) => String(entry)) : []);
    if (next.has(optionValue)) {
      next.delete(optionValue);
    } else {
      next.add(optionValue);
    }
    onValueChange(Array.from(next));
  };

  const handleFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    const list = Array.from(event.target.files ?? []);
    if (list.length) {
      onFileChange(list);
    }
    event.target.value = "";
  };

  return (
    <div className="space-y-2">
      <div className="space-y-1">
        <label className="text-sm font-semibold text-white/90">
          {field.label}
          {field.required ? <span className="ml-1 text-brand-accent">*</span> : null}
        </label>
        {field.helper_text ? <p className="text-xs text-white/60">{field.helper_text}</p> : null}
      </div>

      {renderField()}

      {error ? <p className="text-xs text-rose-400">{error}</p> : null}
    </div>
  );

  function renderField() {
    switch (field.type) {
      case "text":
        return (
          <input
            type="text"
            value={typeof value === "string" ? value : ""}
            onChange={handleTextChange}
            placeholder={field.placeholder}
            disabled={disabled}
            className="w-full rounded-xl border border-white/15 bg-black/20 px-4 py-2 text-sm text-white placeholder:text-white/40 focus:border-brand-accent/40 focus:outline-none"
          />
        );
      case "textarea":
        return (
          <textarea
            value={typeof value === "string" ? value : ""}
            onChange={handleTextChange}
            placeholder={field.placeholder}
            disabled={disabled}
            rows={4}
            className="w-full rounded-xl border border-white/15 bg-black/20 px-4 py-2 text-sm text-white placeholder:text-white/40 focus:border-brand-accent/40 focus:outline-none"
          />
        );
      case "number":
        return (
          <input
            type="number"
            value={typeof value === "number" ? value : value ? Number(value) : ""}
            onChange={handleNumberChange}
            placeholder={field.placeholder}
            disabled={disabled}
            className="w-full rounded-xl border border-white/15 bg-black/20 px-4 py-2 text-sm text-white placeholder:text-white/40 focus:border-brand-accent/40 focus:outline-none"
          />
        );
      case "image":
        return (
          <div className="space-y-2">
            <label
              className={clsx(
                buttonBase,
                "inline-flex cursor-pointer items-center gap-2 bg-white/10 text-white"
              )}
            >
              <input
                type="file"
                className="hidden"
                accept="image/*"
                multiple
                onChange={handleFileInput}
                disabled={disabled}
              />
              Upload images
            </label>
            {files.length ? (
              <ul className="space-y-1 text-xs text-white/70">
                {files.map((file) => (
                  <li key={`${file.name}-${file.lastModified}`}>{file.name}</li>
                ))}
              </ul>
            ) : null}
          </div>
        );
      case "multi_select":
        return (
          <div className="flex flex-wrap gap-2">
            {options.map((option) => {
              const optionKey = normalizeOptionValue(option.value);
              const selected = Array.isArray(value)
                ? value.some((entry) => normalizeOptionValue(entry) === optionKey)
                : false;
              return (
                <button
                  key={option.value}
                  type="button"
                  className={clsx(
                    buttonBase,
                    "bg-white/10",
                    selected && "border-brand-accent bg-brand-accent text-slate-900 shadow-[0_0_0_1px_rgba(20,255,204,0.55)]"
                  )}
                  onClick={() => handleMultiSelect(option.value)}
                  disabled={disabled}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        );
      case "boolean":
      case "yes_no":
      case "single_select":
      default:
        return (
          <div className="flex flex-wrap gap-2">
            {(field.type === "boolean" || field.type === "yes_no" ? DEFAULT_BOOLEAN_OPTIONS : options).map((option) => {
              const optionKey = normalizeOptionValue(option.value);
              const selected = normalizeOptionValue(value) === optionKey;
              return (
                <button
                  key={option.value}
                  type="button"
                  className={clsx(
                    buttonBase,
                    "bg-white/10",
                    selected && "border-brand-accent bg-brand-accent text-slate-900 shadow-[0_0_0_1px_rgba(20,255,204,0.55)]"
                  )}
                  onClick={() => handleSingleSelect(option.value)}
                  disabled={disabled}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        );
    }
  }
};

export default FieldRenderer;
