// Client-side chart storage using localStorage.
// No auth required — charts are saved per-browser.

export interface SavedChart {
  id: string;
  name: string;
  date: string;   // "1950-09-19"
  time: string;   // "09:30"
  place: string;
  lat: string;
  lon: string;
  tz: string;
  savedAt: string; // ISO timestamp
  order: number;   // for manual reordering (lower = higher in list)
}

const KEY = "vedicastro_saved_charts";

function read(): SavedChart[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as SavedChart[]) : [];
  } catch {
    return [];
  }
}

function write(charts: SavedChart[]): void {
  localStorage.setItem(KEY, JSON.stringify(charts));
}

export function getSavedCharts(): SavedChart[] {
  return read().sort((a, b) => a.order - b.order);
}

export function saveChart(params: Omit<SavedChart, "id" | "savedAt" | "order">): SavedChart {
  const charts = read();
  const existing = charts.find(
    (c) => c.date === params.date && c.time === params.time && c.lat === params.lat,
  );
  if (existing) return existing; // already saved — return the existing entry

  const chart: SavedChart = {
    ...params,
    id: crypto.randomUUID(),
    savedAt: new Date().toISOString(),
    order: charts.length,
  };
  write([...charts, chart]);
  return chart;
}

export function deleteChart(id: string): void {
  write(read().filter((c) => c.id !== id));
}

export function deleteCharts(ids: Set<string>): void {
  write(read().filter((c) => !ids.has(c.id)));
}

export function moveChart(id: string, direction: "up" | "down"): void {
  const charts = read().sort((a, b) => a.order - b.order);
  const idx = charts.findIndex((c) => c.id === id);
  if (idx === -1) return;
  const swapIdx = direction === "up" ? idx - 1 : idx + 1;
  if (swapIdx < 0 || swapIdx >= charts.length) return;
  // Swap orders
  const tmp = charts[idx].order;
  charts[idx].order = charts[swapIdx].order;
  charts[swapIdx].order = tmp;
  write(charts);
}

export function isAlreadySaved(date: string, time: string, lat: string): boolean {
  return read().some((c) => c.date === date && c.time === time && c.lat === lat);
}
