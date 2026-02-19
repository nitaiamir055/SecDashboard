import { useEffect, useRef } from "react";
import type { Filing } from "../types/filing";
import { impactCategory, formatImpact } from "../types/filing";

export function useNotifications(filings: Filing[]) {
  const lastNotified = useRef<string | null>(null);

  // Request permission on mount
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  // Notify for non-neutral signals
  useEffect(() => {
    if (filings.length === 0) return;
    const latest = filings[0];
    if (latest.is_pending) return;
    if (latest.accession_number === lastNotified.current) return;
    const category = impactCategory(latest.impact);
    if (category === "neutral") return;

    lastNotified.current = latest.accession_number;

    if ("Notification" in window && Notification.permission === "granted") {
      const icon = category === "bullish" ? "\u{1F7E2}" : "\u{1F534}";
      new Notification(`${icon} SEC-Pulse: ${formatImpact(latest.impact)}`, {
        body: `${latest.ticker || latest.company_name} - ${latest.form_type}\n${latest.summary || ""}`,
        tag: latest.accession_number,
      });
    }
  }, [filings]);
}
