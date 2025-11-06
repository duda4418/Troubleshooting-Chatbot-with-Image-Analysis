import { useEffect, useMemo, useState } from "react";
import { ChartBarIcon, CurrencyDollarIcon, SparklesIcon } from "@heroicons/react/24/outline";

import { fetchUsageMetrics, type ApiUsageMetricsResponse } from "api/metrics";

type MetricCard = {
  title: string;
  value: string;
  description: string;
  icon: typeof CurrencyDollarIcon;
};

const UsageOverview = () => {
  const [metrics, setMetrics] = useState<ApiUsageMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);

    fetchUsageMetrics(controller.signal)
      .then((response) => {
        if (controller.signal.aborted) {
          return;
        }
        setMetrics(response);
      })
      .catch((err) => {
        if (controller.signal.aborted) {
          return;
        }
        console.error("Failed to load usage metrics", err);
        setMetrics(null);
        setError("Usage data is temporarily unavailable.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, []);

  const tokenFormatter = useMemo(
    () =>
      new Intl.NumberFormat("en-US", {
        notation: "compact",
        maximumFractionDigits: 1,
      }),
    []
  );

  const currencyFormatter = useMemo(() => {
    const currency = metrics?.totals.currency || "USD";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    });
  }, [metrics?.totals.currency]);

  const cards = useMemo<MetricCard[]>(() => {
    if (error) {
      return [
        {
          title: "Estimated cost",
          value: "N/A",
          description: error,
          icon: CurrencyDollarIcon,
        },
        {
          title: "Tokens processed",
          value: "N/A",
          description: error,
          icon: ChartBarIcon,
        },
        {
          title: "Average feedback",
          value: "N/A",
          description: error,
          icon: SparklesIcon,
        },
      ];
    }

    if (isLoading) {
      return [
        {
          title: "Estimated cost",
          value: "...",
          description: "Loading usage metrics...",
          icon: CurrencyDollarIcon,
        },
        {
          title: "Tokens processed",
          value: "...",
          description: "Loading usage metrics...",
          icon: ChartBarIcon,
        },
        {
          title: "Average feedback",
          value: "...",
          description: "Loading usage metrics...",
          icon: SparklesIcon,
        },
      ];
    }

    if (!metrics) {
      return [
        {
          title: "Estimated cost",
          value: "N/A",
          description: "Usage data not available yet.",
          icon: CurrencyDollarIcon,
        },
        {
          title: "Tokens processed",
          value: "N/A",
          description: "Token analytics will appear once tracking is enabled.",
          icon: ChartBarIcon,
        },
        {
          title: "Average feedback",
          value: "N/A",
          description: "Feedback summaries will display here when collected.",
          icon: SparklesIcon,
        },
      ];
    }

    const { totals, feedback, pricing_configured: pricingConfigured } = metrics;
    const usageRecordsLabel = totals.usage_records === 1 ? "record" : "records";
    const sessionLabel = totals.sessions === 1 ? "conversation" : "conversations";
    const ratedLabel = feedback.rated_sessions === 1 ? "response" : "responses";

    const costValue = pricingConfigured && totals.cost_total > 0
      ? currencyFormatter.format(totals.cost_total)
      : pricingConfigured
        ? currencyFormatter.format(0)
        : "N/A";

    const costDescription = pricingConfigured
      ? totals.usage_records > 0
        ? `Across ${totals.usage_records} usage ${usageRecordsLabel}.`
        : "No usage recorded yet."
      : "Configure model pricing to enable cost estimates.";

    const tokenValue = totals.total_tokens > 0 ? tokenFormatter.format(totals.total_tokens) : "0";
    const tokenDescription = totals.sessions > 0
      ? `Across ${totals.sessions} ${sessionLabel}.`
      : "No token usage captured yet.";

    const averageRating = feedback.average_rating;
  const ratingValue = typeof averageRating === "number" ? `${averageRating.toFixed(1)} / 5` : "N/A";
    const ratingDescription = feedback.rated_sessions > 0
      ? `Based on ${feedback.rated_sessions} ${ratedLabel}.`
      : "No feedback submitted yet.";

    return [
      {
        title: "Estimated cost",
        value: costValue,
        description: costDescription,
        icon: CurrencyDollarIcon,
      },
      {
        title: "Tokens processed",
        value: tokenValue,
        description: tokenDescription,
        icon: ChartBarIcon,
      },
      {
        title: "Average feedback",
        value: ratingValue,
        description: ratingDescription,
        icon: SparklesIcon,
      },
    ];
  }, [currencyFormatter, error, isLoading, metrics, tokenFormatter]);

  return (
    <section className="grid gap-4 rounded-3xl border border-white/10 bg-brand-surface/60 p-6 backdrop-blur md:grid-cols-3">
      {cards.map(({ title, value, description, icon: Icon }) => (
        <article key={title} className="flex flex-col gap-4 rounded-2xl bg-white/5 p-4 text-white/80">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-accent/20 text-brand-accent">
                <Icon className="h-5 w-5" />
              </span>
              <h3 className="text-sm font-semibold text-white/90">{title}</h3>
            </div>
            <span className="text-lg font-semibold text-white">{value}</span>
          </div>
          <p className="text-sm leading-relaxed text-white/70">{description}</p>
        </article>
      ))}
    </section>
  );
};

export default UsageOverview;
