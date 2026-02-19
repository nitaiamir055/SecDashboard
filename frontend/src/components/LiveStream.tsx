import { useRef, useEffect } from "react";
import type { Filing } from "../types/filing";
import FilingCard from "./FilingCard";

export default function LiveStream({ filings }: { filings: Filing[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtTop = useRef(true);

  useEffect(() => {
    if (isAtTop.current && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [filings]);

  const handleScroll = () => {
    if (scrollRef.current) {
      isAtTop.current = scrollRef.current.scrollTop < 10;
    }
  };

  return (
    <div className="panel h-full">
      <div className="panel-header">
        <h2 className="text-sm font-semibold text-gray-300">
          SEC Live Stream
        </h2>
        <span className="text-xs text-gray-500">{filings.length} filings</span>
      </div>
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="panel-body"
      >
        {filings.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-600 text-sm">
            Waiting for filings...
          </div>
        ) : (
          filings.map((f) => (
            <FilingCard key={f.accession_number} filing={f} compact />
          ))
        )}
      </div>
    </div>
  );
}
