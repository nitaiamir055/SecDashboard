import type { Filing, Segment } from "../types/filing";
import { impactCategory } from "../types/filing";

const SEGMENTS: Segment[] = ["catalyst", "whale", "pulse"];

const SEGMENT_LABELS: Record<Segment, string> = {
  catalyst: "Catalyst (8-K)",
  whale: "Whale (13D/13G)",
  pulse: "Pulse (10-Q)",
};

export default function StatsPanel({ filings }: { filings: Filing[] }) {
  const total = filings.length;
  const bySignal = {
    bullish: filings.filter((f) => !f.is_pending && impactCategory(f.impact) === "bullish").length,
    bearish: filings.filter((f) => !f.is_pending && impactCategory(f.impact) === "bearish").length,
    neutral: filings.filter((f) => !f.is_pending && impactCategory(f.impact) === "neutral").length,
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="text-sm font-semibold text-gray-200">
          Overview
        </h2>
        <span className="text-xs text-gray-500">{total} total</span>
      </div>
      <div className="panel-body space-y-4">
        {/* Signal distribution */}
        <div>
          <h3 className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            Signal Distribution
          </h3>
          <div className="flex gap-3">
            <div className="flex-1 text-center p-2 rounded bg-green-500/10 border border-green-500/20">
              <div className="text-lg font-bold text-green-400">
                {bySignal.bullish}
              </div>
              <div className="text-xs text-green-500">Bullish</div>
            </div>
            <div className="flex-1 text-center p-2 rounded bg-red-500/10 border border-red-500/20">
              <div className="text-lg font-bold text-red-400">
                {bySignal.bearish}
              </div>
              <div className="text-xs text-red-500">Bearish</div>
            </div>
            <div className="flex-1 text-center p-2 rounded bg-gray-500/10 border border-gray-500/20">
              <div className="text-lg font-bold text-gray-400">
                {bySignal.neutral}
              </div>
              <div className="text-xs text-gray-500">Neutral</div>
            </div>
          </div>
        </div>

        {/* By segment */}
        <div>
          <h3 className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            By Segment
          </h3>
          <div className="space-y-1">
            {SEGMENTS.map((seg) => {
              const count = filings.filter((f) => f.segment === seg).length;
              const pct = total > 0 ? (count / total) * 100 : 0;
              return (
                <div key={seg} className="flex items-center gap-2 text-xs">
                  <span className="w-28 text-gray-400 truncate">
                    {SEGMENT_LABELS[seg]}
                  </span>
                  <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-blue-500 h-full rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-gray-500 w-6 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
