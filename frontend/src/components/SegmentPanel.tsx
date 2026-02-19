import type { Filing, Segment } from "../types/filing";
import { impactCategory } from "../types/filing";
import FilingCard from "./FilingCard";

const SEGMENT_CONFIG: Record<
  Segment,
  { title: string; icon: string; description: string }
> = {
  catalyst: {
    title: "Catalyst Report",
    icon: "\u26A1",
    description: "8-K Material Events",
  },
  whale: {
    title: "Whale Watch",
    icon: "\uD83D\uDC33",
    description: "13D/13G Institutional Moves",
  },
  pulse: {
    title: "Pulse Check",
    icon: "\uD83D\uDCC8",
    description: "10-Q Quarterly Financials",
  },
};

export default function SegmentPanel({
  segment,
  filings,
}: {
  segment: Segment;
  filings: Filing[];
}) {
  const config = SEGMENT_CONFIG[segment];
  const segmentFilings = filings.filter((f) => f.segment === segment);

  const bullishCount = segmentFilings.filter(
    (f) => !f.is_pending && impactCategory(f.impact) === "bullish"
  ).length;
  const bearishCount = segmentFilings.filter(
    (f) => !f.is_pending && impactCategory(f.impact) === "bearish"
  ).length;

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="text-sm font-semibold text-gray-200">
            {config.icon} {config.title}
          </h2>
          <p className="text-xs text-gray-500">{config.description}</p>
        </div>
        <div className="flex gap-2 text-xs">
          {bullishCount > 0 && (
            <span className="text-green-400">{bullishCount} bull</span>
          )}
          {bearishCount > 0 && (
            <span className="text-red-400">{bearishCount} bear</span>
          )}
          <span className="text-gray-500">{segmentFilings.length} total</span>
        </div>
      </div>
      <div className="panel-body">
        {segmentFilings.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-600 text-xs">
            No {config.description.toLowerCase()} yet
          </div>
        ) : (
          segmentFilings.map((f) => (
            <FilingCard key={f.accession_number} filing={f} />
          ))
        )}
      </div>
    </div>
  );
}
