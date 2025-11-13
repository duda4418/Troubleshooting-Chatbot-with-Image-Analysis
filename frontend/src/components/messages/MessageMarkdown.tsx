import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageMarkdownProps {
  content: string;
}

const paragraph = ({ children }: { children?: ReactNode }) => (
  <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>
);

const unordered = ({ children }: { children?: ReactNode }) => (
  <ul className="mb-3 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>
);

const ordered = ({ children }: { children?: ReactNode }) => (
  <ol className="mb-3 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>
);

const listItem = ({ children }: { children?: ReactNode }) => <li className="leading-relaxed">{children}</li>;

const codeBlock = ({ inline, children }: { inline?: boolean; children?: ReactNode }) =>
  inline ? (
    <code className="rounded-sm bg-black/40 px-1.5 py-0.5 text-xs font-mono">{children}</code>
  ) : (
    <pre className="mb-3 overflow-x-auto rounded-xl bg-black/40 p-3 font-mono text-xs leading-relaxed last:mb-0">
      <code>{children}</code>
    </pre>
  );

const link = ({ href, children }: { href?: string; children?: ReactNode }) => (
  <a href={href} className="text-brand-accent underline underline-offset-2" target="_blank" rel="noreferrer">
    {children}
  </a>
);

const components = {
  p: paragraph,
  ul: unordered,
  ol: ordered,
  li: listItem,
  code: codeBlock,
  a: link
};

const MessageMarkdown = ({ content }: MessageMarkdownProps) => (
  <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
    {content}
  </ReactMarkdown>
);

export default MessageMarkdown;
