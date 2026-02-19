import type { Filing } from "../types/filing";
import { formatImpact, impactCategory } from "../types/filing";

const IMPACT_COLORS = {
  bullish: "text-green-400",
  bearish: "text-red-400",
  neutral: "text-gray-400",
};

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

export default function SummaryModal({
  filing,
  onClose,
}: {
  filing: Filing;
  onClose: () => void;
}) {
  const category = impactCategory(filing.impact);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70" />

      {/* Modal panel */}
      <div
        className="relative z-10 w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-gray-900 border border-gray-700 rounded-lg shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-700">
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold text-gray-100 truncate">
              {filing.ticker ? (
                <>
                  <span className="text-blue-400">${filing.ticker}</span>
                  <span className="text-gray-500 mx-1">—</span>
                  <span>{filing.company_name}</span>
                </>
              ) : (
                filing.company_name
              )}
            </h2>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              <span className="font-mono">{filing.form_type}</span>
              <span>{formatDate(filing.filed_at)}</span>
            </div>
          </div>
          <div className="flex items-center gap-3 ml-4 flex-shrink-0">
            <span
              className={`text-2xl font-bold ${IMPACT_COLORS[category]}`}
            >
              {formatImpact(filing.impact)}
            </span>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-200 transition-colors text-xl leading-none"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-5">
          {/* Full summary */}
          {filing.summary && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                AI Summary
              </h3>
              <p className="text-sm text-gray-200 leading-relaxed">
                {filing.summary}
              </p>
            </div>
          )}

          {/* Signal reasons */}
          {filing.signal_reasons.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Key Factors
              </h3>
              <ul className="space-y-1">
                {filing.signal_reasons.map((reason, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-300">
                    <span className="text-gray-500 flex-shrink-0">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Link to actual filing */}
          {filing.filing_url && (
            <div className="pt-2 border-t border-gray-800">
              <a
                href={filing.filing_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-400 hover:underline"
              >
                View full filing on SEC EDGAR →
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
