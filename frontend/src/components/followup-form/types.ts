import type { FollowUpField, FollowUpFormDescriptor } from "../../types";

export type FieldValue = string | string[] | number | null;

export interface FieldState {
  value: FieldValue;
  files: File[];
}

export interface FollowUpFormSubmission {
  formId?: string;
  fields: FollowUpField[];
  values: Record<string, FieldValue>;
  files: Record<string, File[]>;
  attachments: File[];
}

export interface FollowUpFormProps {
  form: FollowUpFormDescriptor;
  disabled?: boolean;
  onSubmit: (submission: FollowUpFormSubmission) => Promise<void> | void;
  onDismiss?: (form: FollowUpFormDescriptor) => Promise<void> | void;
}
