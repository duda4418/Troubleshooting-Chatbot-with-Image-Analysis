import clsx from "clsx";
import type { MessageMetadata } from "../../types";

interface MessageAttachmentGridProps {
  attachments: NonNullable<MessageMetadata["attachments"]>;
  standalone?: boolean;
}

const MessageAttachmentGrid = ({ attachments, standalone = false }: MessageAttachmentGridProps) => (
  <div className={clsx(
    "grid gap-3",
    standalone ? "grid-cols-1" : "mt-4 sm:grid-cols-2"
  )}>
    {attachments.map((attachment, index) => {
      const key = `${attachment.type}-${attachment.name ?? index}`;
      if (attachment.type === "image" && attachment.base64) {
        const mime = attachment.mime_type ?? "image/png";
        const src = `data:${mime};base64,${attachment.base64}`;
        return (
          <figure key={key} className={clsx(
            "overflow-hidden rounded-xl border border-white/10 shadow-lg shadow-black/20",
            standalone ? "bg-transparent border-white/20" : "bg-black/20"
          )}>
            <img 
              src={src} 
              alt={attachment.name ?? `Attachment ${index + 1}`} 
              className={clsx(
                "w-full object-cover",
                standalone ? "max-h-96 rounded-xl" : "h-48"
              )} 
            />
            {attachment.name && !standalone ? (
              <figcaption className="truncate px-3 py-2 text-xs text-white/70">{attachment.name}</figcaption>
            ) : null}
          </figure>
        );
      }

      if (attachment.type === "image" && attachment.url) {
        return (
          <figure key={key} className={clsx(
            "overflow-hidden rounded-xl border border-white/10 shadow-lg shadow-black/20",
            standalone ? "bg-transparent border-white/20" : "bg-black/20"
          )}>
            <img 
              src={attachment.url} 
              alt={attachment.name ?? `Attachment ${index + 1}`} 
              className={clsx(
                "w-full object-cover",
                standalone ? "max-h-96 rounded-xl" : "h-48"
              )} 
            />
            {attachment.name && !standalone ? (
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
