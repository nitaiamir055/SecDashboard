import { useState } from "react";
import type { Filing } from "../types/filing";
import { impactCategory } from "../types/filing";
import SignalBadge from "./SignalBadge";
import SummaryModal from "./SummaryModal";

const BORDER_COLORS = {
  bullish: "border-l-green-500 bg-green-500/5",
  bearish: "border-l-red-500 bg-red-500/5",
  neutral: "border-l-gray-600 bg-gray-800/50",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ago`;
}

export default function FilingCard({
  filing,
  compact = false,
}: {
  filing: Filing;
  compact?: boolean;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const category = impactCategory(filing.impact);

  if (filing.is_pending) {
    return (
      <div className="border-l-4 border-l-gray-600 bg-gray-800/50 rounded p-3 mb-2 animate-pulse">
        <div className="flex justify-between items-start gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-sm truncate">
              {filing.ticker ? (
                <>
                  <span className="text-blue-400">${filing.ticker}</span>
                  <span className="text-gray-500 mx-1">-</span>
                  <span className="text-gray-200">{filing.company_name}</span>
                </>
              ) : (
                <span className="text-gray-200">{filing.company_name}</span>
              )}
            </h3>
            <span className="font-mono text-xs text-gray-500">{filing.form_type}</span>
          </div>
          <svg
            className="animate-spin h-4 w-4 text-gray-400 flex-shrink-0"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        </div>
        <p className="text-xs text-gray-500 mt-1.5 italic">Summarization in progress...</p>
        <div className="mt-2 text-xs text-gray-600">{timeAgo(filing.filed_at)}</div>
      </div>
    );
  }

  return (
    <>
      <div
        className={`border-l-4 rounded p-3 mb-2 transition-colors ${BORDER_COLORS[category]}`}
      >
        <div className="flex justify-between items-start gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-sm truncate">
              {filing.ticker ? (
                <>
                  <span className="text-blue-400">${filing.ticker}</span>
                  <span className="text-gray-500 mx-1">-</span>
                  <span className="text-gray-200">{filing.company_name}</span>
                </>
              ) : (
                <span className="text-gray-200">{filing.company_name}</span>
              )}
            </h3>
            <span className="font-mono text-xs text-gray-500">
              {filing.form_type}
            </span>
          </div>
          <SignalBadge impact={filing.impact} />
        </div>

        {filing.summary && (
          <p className="text-xs text-gray-300 mt-1.5 line-clamp-2">
            {filing.summary}
          </p>
        )}

        <div className="flex gap-3 mt-2 text-xs text-gray-500 flex-wrap">
          <span>{timeAgo(filing.filed_at)}</span>
          {filing.latency_ms != null && (
            <span>
              {filing.latency_ms < 15000 ? (
                <span className="text-green-500">{filing.latency_ms}ms</span>
              ) : (
                <span className="text-yellow-500">{filing.latency_ms}ms</span>
              )}
            </span>
          )}
          {filing.summary && (
            <button
              onClick={() => setModalOpen(true)}
              className="text-blue-400 hover:underline"
            >
              Full Summary
            </button>
          )}
          {filing.filing_url && (
            <a
              href={filing.filing_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:underline ml-auto"
            >
              View Filing
            </a>
          )}
        </div>
      </div>

      {modalOpen && (
        <SummaryModal filing={filing} onClose={() => setModalOpen(false)} />
      )}
    </>
  );
}
