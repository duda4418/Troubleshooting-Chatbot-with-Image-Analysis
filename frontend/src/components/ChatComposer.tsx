import { ChangeEvent, FormEvent, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { PaperAirplaneIcon, PhotoIcon } from "@heroicons/react/24/solid";
import { XMarkIcon } from "@heroicons/react/24/outline";
import clsx from "clsx";

interface ChatComposerProps {
  disabled?: boolean;
  placeholder?: string;
  onSend: (payload: {
    message: string;
    attachments: File[];
    metadata?: Record<string, unknown>;
    forceSend?: boolean;
  }) => Promise<void> | void;
}

const MAX_FILE_SIZE_MB = 6;
const MAX_ATTACHMENTS = 4;
const ACCEPTED_TYPES = ["image/*"];

const ChatComposer = ({ disabled = false, placeholder, onSend }: ChatComposerProps) => {
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [previews, setPreviews] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const nextPreviews = selectedFiles.map((file) => URL.createObjectURL(file));
    setPreviews(nextPreviews);
    return () => {
      nextPreviews.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [selectedFiles]);

  const canSend = useMemo(() => value.trim().length > 0 || selectedFiles.length > 0, [value, selectedFiles]);

  const resizeTextarea = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "auto";
    const maxHeight = 240;
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${nextHeight}px`;
  }, []);

  useLayoutEffect(() => {
    resizeTextarea();
  }, [value, resizeTextarea]);

  const resetComposer = () => {
    setValue("");
    setSelectedFiles([]);
    setFileError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = value.trim();

    if (!canSend || disabled || isSubmitting) {
      return;
    }

    const payload = { message: trimmed, attachments: selectedFiles };
    const previousValue = value;
    const previousFiles = [...selectedFiles];

    try {
      setIsSubmitting(true);
      resetComposer();
      await onSend(payload);
    } catch (error) {
      setValue(previousValue);
      setSelectedFiles(previousFiles);
    } finally {
      setIsSubmitting(false);
    }
  };

  const validateFile = (file: File): string | null => {
    if (!file.type.startsWith("image/")) {
      return "Only image uploads are supported.";
    }
    if (file.size / (1024 * 1024) > MAX_FILE_SIZE_MB) {
      return `Images must be smaller than ${MAX_FILE_SIZE_MB}MB.`;
    }
    return null;
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) {
      return;
    }

    const remainingSlots = MAX_ATTACHMENTS - selectedFiles.length;
    if (remainingSlots <= 0) {
      setFileError(`You can attach up to ${MAX_ATTACHMENTS} images per message.`);
      return;
    }

    const nextFiles: File[] = [];
    for (const file of files.slice(0, remainingSlots)) {
      const validationError = validateFile(file);
      if (validationError) {
        setFileError(validationError);
        continue;
      }

      const alreadyPresent = selectedFiles.some(
        (existing) => existing.name === file.name && existing.size === file.size && existing.lastModified === file.lastModified
      );
      if (!alreadyPresent) {
        nextFiles.push(file);
      }
    }

    if (nextFiles.length) {
      setSelectedFiles((prev) => [...prev, ...nextFiles]);
      setFileError(null);
    }

    event.target.value = "";
  };

  const handleRemoveAttachment = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== index));
    setFileError(null);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-brand-surfaceAlt/80 p-4 text-brand-secondary shadow-lg shadow-black/20"
    >
      {fileError ? <p className="text-sm text-rose-400">{fileError}</p> : null}

      {selectedFiles.length ? (
        <div className="max-h-48 overflow-y-auto pr-1 scrollbar-thin">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {selectedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/25 p-3 text-white/90"
              >
                <div className="h-12 w-12 overflow-hidden rounded-lg border border-white/10 bg-black/20">
                  <img src={previews[index] ?? ""} alt={`Attachment ${index + 1}`} className="h-full w-full object-cover" />
                </div>
                <div className="flex-1 text-sm">
                  <p className="truncate font-medium" title={file.name}>
                    {file.name}
                  </p>
                  <p className="text-xs text-brand-secondary/70">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveAttachment(index)}
                  className="rounded-full border border-white/15 p-1 text-brand-secondary transition hover:text-white"
                  aria-label={`Remove attachment ${file.name}`}
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="flex items-end gap-3">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className={clsx(
            "flex h-11 w-11 items-center justify-center rounded-xl border border-dashed border-white/20 bg-black/20",
            "text-brand-secondary transition hover:border-brand-accent hover:text-brand-accent"
          )}
          disabled={disabled || isSubmitting}
          aria-label="Attach images"
        >
          <PhotoIcon className="h-5 w-5" />
        </button>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setValue(event.target.value)}
          onInput={resizeTextarea}
          placeholder={placeholder ?? "Describe the issue you need help with..."}
          rows={1}
          className="scrollbar-muted max-h-60 min-h-[44px] w-full resize-none overflow-y-auto rounded-xl border border-transparent bg-black/10 px-4 py-2 text-sm leading-relaxed text-white outline-none placeholder:text-brand-secondary/50 focus:border-brand-accent/50 focus:bg-black/15"
          disabled={disabled || isSubmitting}
        />

        <button
          type="submit"
          className={clsx(
            "flex h-11 w-11 items-center justify-center rounded-full bg-brand-accent text-white transition",
            "hover:bg-brand-accentHover disabled:cursor-not-allowed disabled:bg-brand-accent/40"
          )}
          disabled={disabled || isSubmitting || !canSend}
          aria-label="Send message"
        >
          <PaperAirplaneIcon className="h-4 w-4" />
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
  accept={ACCEPTED_TYPES.join(",")}
        multiple
        className="hidden"
        onChange={handleFileChange}
      />
    </form>
  );
};

export default ChatComposer;
