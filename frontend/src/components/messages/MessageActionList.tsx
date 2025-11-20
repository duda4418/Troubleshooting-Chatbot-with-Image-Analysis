interface MessageActionListProps {
  suggestedActions: string[];
}

const MessageActionList = ({ suggestedActions }: MessageActionListProps) => (
  <div className="mt-4 rounded-2xl border border-white/15 bg-black/20 p-4 text-white/90">
    <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-white/70">Suggested Actions</p>
    <ul className="list-disc space-y-2 pl-5 marker:text-brand-accent marker:text-sm">
      {suggestedActions.map((action) => (
        <li key={action} className="leading-relaxed">
          {action}
        </li>
      ))}
    </ul>
  </div>
);

export default MessageActionList;
