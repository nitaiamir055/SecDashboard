import type { Filing, Segment } from "../types/filing";
import LiveStream from "./LiveStream";
import SegmentPanel from "./SegmentPanel";
import StatsPanel from "./StatsPanel";

const SEGMENTS: Segment[] = ["catalyst", "whale", "pulse"];

export default function Dashboard({
  filings,
  connected,
}: {
  filings: Filing[];
  connected: boolean;
}) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight">SEC-Pulse</h1>
          <span className="text-xs text-gray-500 hidden sm:inline">
            Real-Time Market Intelligence
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div
              className={`w-2 h-2 rounded-full ${
                connected ? "bg-green-500 animate-pulse" : "bg-red-500"
              }`}
            />
            <span className="text-xs text-gray-400">
              {connected ? "Live" : "Disconnected"}
            </span>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="flex-1 grid grid-cols-12 gap-3 p-3 min-h-0">
        {/* Left: Live Stream */}
        <div className="col-span-12 lg:col-span-4 xl:col-span-3 min-h-[400px] lg:min-h-0">
          <LiveStream filings={filings} />
        </div>

        {/* Right: 3 Segment Panels + Stats */}
        <div className="col-span-12 lg:col-span-8 xl:col-span-9 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-3 min-h-0">
          {SEGMENTS.map((seg) => (
            <SegmentPanel key={seg} segment={seg} filings={filings} />
          ))}
          <StatsPanel filings={filings} />
        </div>
      </div>
    </div>
  );
}
