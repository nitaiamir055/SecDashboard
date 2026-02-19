export type Segment = "catalyst" | "whale" | "pulse";
export type ImpactCategory = "bullish" | "bearish" | "neutral";

/** Derive a color category from a numeric impact score. */
export function impactCategory(score: number | null | undefined): ImpactCategory {
  if (score == null) return "neutral";
  if (score > 20) return "bullish";
  if (score < -20) return "bearish";
  return "neutral";
}

/** Format a numeric impact score with a +/- prefix. */
export function formatImpact(score: number | null | undefined): string {
  if (score == null) return "0";
  return score > 0 ? `+${score}` : `${score}`;
}

export interface Filing {
  id: number;
  accession_number: string;
  form_type: string;
  segment: Segment;
  company_name: string;
  cik: string;
  ticker: string | null;
  filing_url: string;
  filed_at: string;
  latency_ms: number | null;
  summary: string | null;
  impact: number | null;
  signal_reasons: string[];
  metadata: Record<string, unknown>;
  is_pending?: boolean;
}

export type WSMessage =
  | { type: "new_filing"; data: Filing }
  | {
      type: "filing_processing";
      data: {
        accession_number: string;
        company_name: string;
        ticker: string | null;
        form_type: string;
        segment: Segment;
        filed_at: string;
      };
    };
