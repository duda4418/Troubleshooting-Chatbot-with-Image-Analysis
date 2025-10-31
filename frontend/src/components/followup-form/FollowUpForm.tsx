import { FormEvent, useEffect, useState } from "react";
import clsx from "clsx";
import type {
  FollowUpField,
  FollowUpFormDescriptor,
  FollowUpFormSubmissionState,
  FollowUpFormStatus
} from "../../types";
import FieldRenderer from "./FieldRenderer";
import { coerceInitialState } from "./helpers";
import type { FieldState, FieldValue, FollowUpFormProps, FollowUpFormSubmission } from "./types";

const FollowUpForm = ({ form, disabled = false, onSubmit, onDismiss }: FollowUpFormProps) => {
  const [fieldState, setFieldState] = useState<Record<string, FieldState>>(() =>
    initializeState(form.fields, form.submission)
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<FollowUpFormStatus>(resolveInitialStatus(form));
  const isSingleQuestion = form.fields.length === 1;
  const showHeader = !isSingleQuestion && (form.title || form.description);
  const isCompact = isSingleQuestion;

  useEffect(() => {
    setFieldState(initializeState(form.fields, form.submission));
    setStatus(resolveInitialStatus(form));
    setErrors({});
  }, [form]);

  const hasFields = form.fields.length > 0;

  if (status !== "in_progress" || !hasFields) {
    return null;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || isSubmitting) {
      return;
    }

    const nextErrors: Record<string, string> = {};
    const values: Record<string, FieldState> = {};

    form.fields.forEach((field) => {
      const current = fieldState[field.id] ?? coerceInitialState(field);
      values[field.id] = current;
      if (!field.required) {
        return;
      }
      switch (field.type) {
        case "multi_select":
          if (!Array.isArray(current.value) || current.value.length === 0) {
            nextErrors[field.id] = "Select at least one option.";
          }
          break;
        case "image":
          if (!current.files.length) {
            nextErrors[field.id] = "Please attach at least one image.";
          }
          break;
        case "number":
          if (current.value === null || current.value === "") {
            nextErrors[field.id] = "Enter a number.";
          }
          break;
        default:
          if (!current.value || String(current.value).trim().length === 0) {
            nextErrors[field.id] = "Provide an answer.";
          }
          break;
      }
    });

    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }

    setErrors({});

    const submission = compileSubmission(form.fields, values);
    const payload: FollowUpFormSubmission = {
      ...submission,
      formId: form.id
    };

    try {
      setIsSubmitting(true);
      await onSubmit(payload);
      setStatus("submitted");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleValueChange = (field: FollowUpField, value: FieldValue) => {
    setFieldState((prev) => {
      const next: Record<string, FieldState> = { ...prev };
      const current = next[field.id] ?? coerceInitialState(field);
      next[field.id] = {
        value,
        files: current.files
      };
      return next;
    });
  };

  const handleFileChange = (field: FollowUpField, files: File[]) => {
    setFieldState((prev) => {
      const next: Record<string, FieldState> = { ...prev };
      const current = next[field.id] ?? coerceInitialState(field);
      next[field.id] = {
        value: current.value,
        files
      };
      return next;
    });
  };

  const handleDismiss = async () => {
    if (!onDismiss || disabled || isSubmitting) {
      return;
    }
    try {
      setIsSubmitting(true);
      await onDismiss(form);
      setStatus("dismissed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={clsx(
        "mt-4 rounded-2xl border border-brand-accent/20 bg-black/10",
        isCompact ? "space-y-3 p-3" : "space-y-4 p-4"
      )}
    >
        {showHeader ? (
        <header className="space-y-1">
          {form.title ? <h3 className="text-base font-semibold text-white/85">{form.title}</h3> : null}
          {form.description ? <p className="text-sm text-white/55">{form.description}</p> : null}
        </header>
        ) : null}

      <div className="space-y-3">
        {form.fields.map((field) => {
          const state = fieldState[field.id] ?? coerceInitialState(field);
          return (
            <FieldRenderer
              key={field.id}
              field={field}
              value={state.value}
              files={state.files}
              disabled={disabled || isSubmitting}
              error={errors[field.id]}
              onValueChange={(next) => handleValueChange(field, next)}
              onFileChange={(next) => handleFileChange(field, next)}
            />
          );
        })}
      </div>

      <div className="flex flex-wrap justify-end gap-2">
        {onDismiss ? (
          <button
            type="button"
            onClick={handleDismiss}
            className={clsx(
              "rounded-full border border-white/25 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-white/70 transition",
              (disabled || isSubmitting) && "opacity-60"
            )}
            disabled={disabled || isSubmitting}
          >
            Dismiss
          </button>
        ) : null}
        <button
          type="submit"
          className={clsx(
            "rounded-full bg-brand-accent px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-white transition",
            (disabled || isSubmitting) && "opacity-70"
          )}
          disabled={disabled || isSubmitting}
        >
          Submit
        </button>
      </div>
    </form>
  );
};

const resolveInitialStatus = (form: FollowUpFormDescriptor): FollowUpFormStatus =>
  form.status ?? form.submission?.status ?? "in_progress";

const initializeState = (
  fields: FollowUpField[],
  submission?: FollowUpFormSubmissionState | null
): Record<string, FieldState> => {
  const map: Record<string, FieldState> = {};
  fields.forEach((field) => {
    const base = coerceInitialState(field);
    const existing = submission?.fields.find((entry) => entry.id === field.id);
    if (existing) {
      base.value = toFieldValue(existing.value, field.type);
    }
    map[field.id] = base;
  });
  return map;
};

const compileSubmission = (
  fields: FollowUpField[],
  state: Record<string, FieldState>
): FollowUpFormSubmission => {
  const values: Record<string, FieldValue> = {};
  const files: Record<string, File[]> = {};
  const attachments: File[] = [];

  fields.forEach((field) => {
    const current = state[field.id] ?? coerceInitialState(field);
    values[field.id] = current.value;
    if (current.files.length) {
      files[field.id] = current.files;
      attachments.push(...current.files);
    }
  });

  return {
    fields,
    values,
    files,
    attachments
  };
};

const toFieldValue = (value: string | number | string[] | null, type: FollowUpField["type"]): FieldValue => {
  if (value === null || value === undefined) {
    switch (type) {
      case "multi_select":
        return [];
      case "number":
        return null;
      default:
        return "";
    }
  }

  if (Array.isArray(value)) {
    return value.map((item) => String(item));
  }

  if (type === "number") {
    const parsed = typeof value === "number" ? value : Number(value);
    return Number.isNaN(parsed) ? null : parsed;
  }

  return String(value);
};

export default FollowUpForm;
