import { impactCategory, formatImpact } from "../types/filing";

const BADGE_STYLES = {
  bullish: "bg-green-500/20 text-green-400 border-green-500/30",
  bearish: "bg-red-500/20 text-red-400 border-red-500/30",
  neutral: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

export default function SignalBadge({ impact }: { impact: number | null | undefined }) {
  const category = impactCategory(impact);
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${BADGE_STYLES[category]}`}
    >
      {formatImpact(impact)}
    </span>
  );
}
