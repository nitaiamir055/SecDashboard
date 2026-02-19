import { useState, useEffect, useRef, useCallback } from "react";
import type { Filing, WSMessage } from "../types/filing";

const MAX_FILINGS = 200;
const RECONNECT_DELAY = 2000;

export function useWebSocket(url: string) {
  const [filings, setFilings] = useState<Filing[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number>();

  // Load existing filings from the REST API on mount (merges with any WS data already received)
  useEffect(() => {
    fetch("/api/filings?limit=200")
      .then((r) => r.json())
      .then((data: Filing[]) => {
        if (!Array.isArray(data) || data.length === 0) return;
        setFilings((prev) => {
          const accSet = new Set(prev.map((f) => f.accession_number));
          const incoming = data.filter((f) => !accSet.has(f.accession_number));
          return [...prev, ...incoming].slice(0, MAX_FILINGS);
        });
      })
      .catch(() => {/* backend may not be ready yet */});
  }, []);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = window.setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);

        if (msg.type === "filing_processing") {
          // Insert a pending placeholder card
          const placeholder: Filing = {
            id: -1,
            accession_number: msg.data.accession_number,
            form_type: msg.data.form_type,
            segment: msg.data.segment,
            company_name: msg.data.company_name,
            cik: "",
            ticker: msg.data.ticker,
            filing_url: "",
            filed_at: msg.data.filed_at,
            latency_ms: null,
            summary: null,
            impact: null,
            signal_reasons: [],
            metadata: {},
            is_pending: true,
          };
          setFilings((prev) => {
            if (prev.some((f) => f.accession_number === placeholder.accession_number)) {
              return prev;
            }
            return [placeholder, ...prev].slice(0, MAX_FILINGS);
          });
        } else if (msg.type === "new_filing") {
          setFilings((prev) => {
            // Replace a pending card if present, otherwise prepend
            const idx = prev.findIndex(
              (f) => f.accession_number === msg.data.accession_number
            );
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = msg.data;
              return next;
            }
            return [msg.data, ...prev].slice(0, MAX_FILINGS);
          });
        }
      } catch {
        // Ignore malformed messages
      }
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  return { filings, connected };
}
