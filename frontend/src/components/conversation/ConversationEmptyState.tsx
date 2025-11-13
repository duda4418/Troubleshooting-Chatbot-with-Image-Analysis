interface ConversationEmptyStateProps {
  title: string;
  description: string;
}

const ConversationEmptyState = ({ title, description }: ConversationEmptyStateProps) => (
  <div className="flex h-full flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-brand-border/40 bg-black/20 p-10 text-center text-brand-secondary/70">
    <p className="text-base font-medium text-white/90">{title}</p>
    <p className="max-w-md text-sm">{description}</p>
  </div>
);

export default ConversationEmptyState;
