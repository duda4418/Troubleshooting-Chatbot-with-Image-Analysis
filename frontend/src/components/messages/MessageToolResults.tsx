import type { ToolCallMetadata } from "../../types";

interface MessageToolResultsProps {
  results: ToolCallMetadata[];
}

const MessageToolResults = ({ results }: MessageToolResultsProps) => (
  <div className="mt-4 space-y-3 text-sm text-white/90">
    {results.map((result) => (
      <div key={`${result.tool}-${result.summary ?? ""}`} className="rounded-2xl border border-white/10 bg-black/20 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-white/70">{result.tool ?? "Tool"}</p>
        {result.summary ? <p className="mt-2 text-sm leading-relaxed">{result.summary}</p> : null}
        {typeof result.success === "boolean" ? (
          <span className="mt-3 inline-flex items-center rounded-full bg-white/10 px-3 py-1 text-xs uppercase tracking-wide">
            {result.success ? "Success" : "Failed"}
          </span>
        ) : null}
      </div>
    ))}
  </div>
);

export default MessageToolResults;
