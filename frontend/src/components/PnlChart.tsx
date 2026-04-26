import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  AreaSeries,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from "lightweight-charts";

interface PnlPoint {
  time: Time;
  value: number;
}

interface PnlChartProps {
  data: PnlPoint[];
  height?: number;
}

export default function PnlChart({ data, height = 220 }: PnlChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#64748b",
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
      timeScale: { borderColor: "#252836", timeVisible: true },
      height,
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#6366f1",
      topColor: "rgba(99,102,241,0.25)",
      bottomColor: "rgba(99,102,241,0)",
      lineWidth: 2,
      priceLineVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = series;

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
  }, [height]);

  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      seriesRef.current.setData(data);
    }
  }, [data]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
