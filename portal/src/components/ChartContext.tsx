"use client";

import { createContext, useContext, useState, useCallback } from "react";
import type { ChartData } from "@/lib/types";

interface ChartContextType {
  chart: ChartData | null;
  setChartData: (data: ChartData) => void;
  isLoading: boolean;
  setIsLoading: (v: boolean) => void;
}

const ChartContext = createContext<ChartContextType>({
  chart: null, setChartData: () => {}, isLoading: false, setIsLoading: () => {},
});

export function ChartProvider({ children }: { children: React.ReactNode }) {
  const [chart, setChart] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const setChartData = useCallback((data: ChartData) => setChart(data), []);
  return (
    <ChartContext.Provider value={{ chart, setChartData, isLoading, setIsLoading }}>
      {children}
    </ChartContext.Provider>
  );
}

export function useChart() {
  return useContext(ChartContext);
}
