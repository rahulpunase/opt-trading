import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  createChart,
  ColorType,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import { api, type CandleBar } from "@/lib/api";
import { useSymbolQuote } from "@/hooks/useSymbolQuote";

export type Timeframe =
  | "1min"
  | "3min"
  | "5min"
  | "15min"
  | "30min"
  | "60min"
  | "1d";

const TIMEFRAMES: { label: string; value: Timeframe }[] = [
  { label: "1m", value: "1min" },
  { label: "3m", value: "3min" },
  { label: "5m", value: "5min" },
  { label: "15m", value: "15min" },
  { label: "30m", value: "30min" },
  { label: "1h", value: "60min" },
  { label: "1D", value: "1d" },
];

const TF_MINUTES: Record<Timeframe, number> = {
  "1min": 1,
  "3min": 3,
  "5min": 5,
  "15min": 15,
  "30min": 30,
  "60min": 60,
  "1d": 1440,
};

interface OhlcChartProps {
  instrumentToken: number;
  symbol: string;
  defaultTimeframe?: Timeframe;
  height?: number;
  showVolume?: boolean;
}

export default function OhlcChart({
  instrumentToken,
  symbol,
  defaultTimeframe = "5min",
  height = 400,
  showVolume = true,
}: OhlcChartProps) {
  const [timeframe, setTimeframe] = useState<Timeframe>(defaultTimeframe);

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  // Live candle being built from ticks; keyed by bucket start time (Unix seconds)
  const currentCandleRef = useRef<CandleBar | null>(null);

  const { data: candles, isLoading } = useQuery({
    queryKey: ["candles", instrumentToken, timeframe],
    queryFn: () => api.instrumentCandles(instrumentToken, timeframe, 300),
    enabled: instrumentToken > 0,
    refetchOnWindowFocus: false,
    retry: 1,
    staleTime: 60_000,
  });

  const { tick } = useSymbolQuote(instrumentToken, symbol);

  // Initialize chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const candleHeight = showVolume ? Math.round(height * 0.75) : height;
    const volHeight = showVolume ? height - candleHeight : 0;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#64748b",
      },
      localization: {
        timeFormatter: (time: number) =>
          new Date(time * 1000).toLocaleTimeString("en-IN", {
            timeZone: "Asia/Kolkata",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          }),
      },
      grid: {
        vertLines: { color: "#252836" },
        horzLines: { color: "#252836" },
      },
      crosshair: {
        vertLine: { color: "#6366f1" },
        horzLine: { color: "#6366f1" },
      },
      rightPriceScale: { borderColor: "#252836" },
      timeScale: {
        borderColor: "#252836",
        timeVisible: true,
        tickMarkFormatter: (time: number) =>
          new Date(time * 1000).toLocaleTimeString("en-IN", {
            timeZone: "Asia/Kolkata",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          }),
      },
      height: candleHeight,
    });
    chart.timeScale().fitContent();

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    if (showVolume) {
      const volChart = createChart(containerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "#64748b",
        },
        localization: {
          timeFormatter: (time: number) =>
            new Date(time * 1000).toLocaleTimeString("en-IN", {
              timeZone: "Asia/Kolkata",
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            }),
        },
        grid: {
          vertLines: { color: "#252836" },
          horzLines: { color: "#252836" },
        },
        rightPriceScale: {
          borderColor: "#252836",
          scaleMargins: { top: 0.1, bottom: 0 },
        },
        timeScale: {
          borderColor: "#252836",
          timeVisible: true,
          tickMarkFormatter: (time: number) =>
            new Date(time * 1000).toLocaleTimeString("en-IN", {
              timeZone: "Asia/Kolkata",
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            }),
        },
        height: volHeight,
        crosshair: {
          vertLine: { color: "#6366f1" },
          horzLine: { visible: false },
        },
      });

      const volSeries = volChart.addSeries(HistogramSeries, {
        color: "#6366f150",
        priceFormat: { type: "volume" },
      });

      volumeSeriesRef.current = volSeries;

      // Sync time scales
      chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) volChart.timeScale().setVisibleLogicalRange(range);
      });
      volChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) chart.timeScale().setVisibleLogicalRange(range);
      });

      const ro = new ResizeObserver(() => {
        if (!containerRef.current) return;
        const w = containerRef.current.clientWidth;
        chart.applyOptions({ width: w });
        volChart.applyOptions({ width: w });
      });
      ro.observe(containerRef.current);

      return () => {
        ro.disconnect();
        volChart.remove();
        chart.remove();
      };
    }

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [height, showVolume]);

  // Clear series immediately when timeframe switches so stale candles can't
  // block tick updates before the new historical data arrives.
  useEffect(() => {
    candleSeriesRef.current?.setData([]);
    volumeSeriesRef.current?.setData([]);
    currentCandleRef.current = null;
  }, [timeframe]);

  // Load historical data into series whenever query result changes
  useEffect(() => {
    if (!candles?.length) return;
    currentCandleRef.current = null;

    if (candleSeriesRef.current) {
      candleSeriesRef.current.setData(
        candles.map((c) => ({
          time: c.time as unknown as import("lightweight-charts").Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })),
      );
    }
    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.setData(
        candles.map((c) => ({
          time: c.time as unknown as import("lightweight-charts").Time,
          value: c.volume,
          color: c.close >= c.open ? "#22c55e50" : "#ef444450",
        })),
      );
    }

    chartRef.current?.timeScale().scrollToRealTime();
  }, [candles]);

  // Aggregate live ticks into the current open candle
  useEffect(() => {
    if (!tick || !candleSeriesRef.current) return;

    const nowSec = Math.floor(Date.now() / 1000);
    const tfMin = TF_MINUTES[timeframe];
    const bucketStart = Math.floor(nowSec / (tfMin * 60)) * (tfMin * 60);

    const ltp = tick.ltp;
    const vol = tick.volume ?? 0;

    const cur = currentCandleRef.current;
    if (!cur || cur.time !== bucketStart) {
      // New bucket — start fresh candle
      const newCandle: CandleBar = {
        time: bucketStart,
        open: ltp,
        high: ltp,
        low: ltp,
        close: ltp,
        volume: vol,
      };
      currentCandleRef.current = newCandle;
      candleSeriesRef.current.update({
        time: bucketStart as unknown as import("lightweight-charts").Time,
        open: ltp,
        high: ltp,
        low: ltp,
        close: ltp,
      });
    } else {
      // Update existing bucket
      cur.high = Math.max(cur.high, ltp);
      cur.low = Math.min(cur.low, ltp);
      cur.close = ltp;
      cur.volume = vol;
      candleSeriesRef.current.update({
        time: bucketStart as unknown as import("lightweight-charts").Time,
        open: cur.open,
        high: cur.high,
        low: cur.low,
        close: cur.close,
      });
    }

    if (volumeSeriesRef.current && currentCandleRef.current) {
      const c = currentCandleRef.current;
      volumeSeriesRef.current.update({
        time: bucketStart as unknown as import("lightweight-charts").Time,
        value: c.volume,
        color: c.close >= c.open ? "#22c55e50" : "#ef444450",
      });
    }
  }, [tick, timeframe]);

  return (
    <div className="rounded-xl border border-border bg-bg-surface overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <span className="text-xs font-medium text-text-muted">Price Chart</span>
        <div className="flex gap-1">
          {TIMEFRAMES.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => setTimeframe(value)}
              className={`rounded px-2 py-0.5 text-xs font-medium transition ${
                timeframe === value
                  ? "bg-accent text-white"
                  : "bg-bg-elevated text-text-muted hover:text-text-primary"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart container */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg-surface/60">
            <span className="text-xs text-text-muted">Loading…</span>
          </div>
        )}
        <div ref={containerRef} className="w-full" />
      </div>
    </div>
  );
}
