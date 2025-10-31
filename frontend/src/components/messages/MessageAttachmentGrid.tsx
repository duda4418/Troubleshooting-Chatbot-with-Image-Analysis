import type { MessageMetadata } from "../../types";

interface MessageAttachmentGridProps {
  attachments: NonNullable<MessageMetadata["attachments"]>;
}

const MessageAttachmentGrid = ({ attachments }: MessageAttachmentGridProps) => (
  <div className="mt-4 grid gap-3 sm:grid-cols-2">
    {attachments.map((attachment, index) => {
      const key = `${attachment.type}-${attachment.name ?? index}`;
      if (attachment.type === "image" && attachment.base64) {
        const mime = attachment.mime_type ?? "image/png";
        const src = `data:${mime};base64,${attachment.base64}`;
        return (
          <figure key={key} className="overflow-hidden rounded-xl border border-white/10 bg-black/20">
            <img src={src} alt={attachment.name ?? `Attachment ${index + 1}`} className="h-48 w-full object-cover" />
            {attachment.name ? (
              <figcaption className="truncate px-3 py-2 text-xs text-white/70">{attachment.name}</figcaption>
            ) : null}
          </figure>
        );
      }

      if (attachment.type === "image" && attachment.url) {
        return (
          <figure key={key} className="overflow-hidden rounded-xl border border-white/10 bg-black/20">
            <img src={attachment.url} alt={attachment.name ?? `Attachment ${index + 1}`} className="h-48 w-full object-cover" />
            {attachment.name ? (
              <figcaption className="truncate px-3 py-2 text-xs text-white/70">{attachment.name}</figcaption>
            ) : null}
          </figure>
        );
      }

      if (attachment.url) {
        return (
          <a
            key={key}
            href={attachment.url}
            className="flex items-center justify-between rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-white/80"
            target="_blank"
            rel="noreferrer"
          >
            <span className="truncate">{attachment.name ?? `Attachment ${index + 1}`}</span>
            <span className="text-xs uppercase text-white/50">Open</span>
          </a>
        );
      }

      return (
        <div
          key={key}
          className="flex items-center justify-between rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-white/80"
        >
          <span className="truncate">{attachment.name ?? `Attachment ${index + 1}`}</span>
          <span className="text-xs uppercase text-white/50">Attached</span>
        </div>
      );
    })}
  </div>
);

export default MessageAttachmentGrid;
