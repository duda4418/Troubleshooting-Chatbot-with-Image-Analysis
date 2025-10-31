import type { FollowUpField, FollowUpOption } from "../../types";
import type { FieldState } from "./types";

export const DEFAULT_BOOLEAN_OPTIONS: FollowUpOption[] = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" }
];

export const coerceInitialState = (field: FollowUpField): FieldState => {
  switch (field.type) {
    case "multi_select":
      return { value: [], files: [] };
    case "number":
      return { value: null, files: [] };
    case "image":
      return { value: null, files: [] };
    default:
      return { value: "", files: [] };
  }
};

export const resolveOptions = (field: FollowUpField): FollowUpOption[] => {
  if (field.type === "boolean" || field.type === "yes_no") {
    return DEFAULT_BOOLEAN_OPTIONS;
  }
  if (field.options && field.options.length) {
    return field.options;
  }
  if (field.type === "single_select" || field.type === "multi_select") {
    return DEFAULT_BOOLEAN_OPTIONS;
  }
  return [];
};

