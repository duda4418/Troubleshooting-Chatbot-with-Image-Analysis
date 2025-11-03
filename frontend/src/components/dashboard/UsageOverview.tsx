import { ChartBarIcon, CurrencyDollarIcon, SparklesIcon } from "@heroicons/react/24/outline";

const METRIC_CARDS = [
  {
    title: "Estimated cost",
    description: "Usage data not available yet.",
    icon: CurrencyDollarIcon,
  },
  {
    title: "Tokens processed",
    description: "Token analytics will appear once tracking is enabled.",
    icon: ChartBarIcon,
  },
  {
    title: "Average feedback",
    description: "Feedback summaries will display here when collected.",
    icon: SparklesIcon,
  },
];

const UsageOverview = () => (
  <section className="grid gap-4 rounded-3xl border border-white/10 bg-brand-surface/60 p-6 backdrop-blur md:grid-cols-3">
    {METRIC_CARDS.map(({ title, description, icon: Icon }) => (
      <article key={title} className="flex flex-col gap-3 rounded-2xl bg-white/5 p-4 text-white/80">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-accent/20 text-brand-accent">
            <Icon className="h-5 w-5" />
          </span>
          <h3 className="text-sm font-semibold text-white/90">{title}</h3>
        </div>
        <p className="text-sm leading-relaxed text-white/70">{description}</p>
      </article>
    ))}
  </section>
);

export default UsageOverview;
