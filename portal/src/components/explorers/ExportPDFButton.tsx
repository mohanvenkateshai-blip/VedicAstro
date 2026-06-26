"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import type { ChartData } from "@/lib/types";
import { RASHIS } from "@/lib/types";
import { Button } from "@/components/ui/Button";

const PLANET_COLORS: Record<string, string> = {
  Sun: "#f59e0b",
  Moon: "#c0c0c0",
  Mars: "#ef4444",
  Mercury: "#22c55e",
  Jupiter: "#c5a46e",
  Venus: "#ec4899",
  Saturn: "#6b7280",
  Rahu: "#8b5cf6",
  Ketu: "#14b8a6",
};

const PLANET_SHORT: Record<string, string> = {
  Sun: "Su",
  Moon: "Mo",
  Mars: "Ma",
  Mercury: "Me",
  Jupiter: "Ju",
  Venus: "Ve",
  Saturn: "Sa",
  Rahu: "Ra",
  Ketu: "Ke",
  Lagna: "La",
  Ascendant: "As",
};

const RASHI_SHORT = [
  "Ar",
  "Ta",
  "Ge",
  "Ca",
  "Le",
  "Vi",
  "Li",
  "Sc",
  "Sg",
  "Cp",
  "Aq",
  "Pi",
] as const;

function renderSouthChartSVG(signs: Record<string, number>, size: number): string {
  const CS = size / 4;
  const lagnaSign = signs.Lagna ?? signs.Ascendant ?? 0;
  const PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"];

  const occ: Record<number, string[]> = {};
  for (const p of PLANET_ORDER) {
    const s = signs[p];
    if (s == null) continue;
    (occ[s] ??= []).push(PLANET_SHORT[p] ?? p.slice(0, 2));
  }

  const layout = [
    [11, 0, 1, 2],
    [10, -1, -1, 3],
    [9, -1, -1, 4],
    [8, 7, 6, 5],
  ];

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`;
  svg += `<rect width="${size}" height="${size}" rx="10" fill="#ffffff" stroke="#1e3a5f" stroke-width="2" />`;

  for (let i = 1; i <= 3; i++) {
    svg += `<line x1="${i * CS}" y1="0" x2="${i * CS}" y2="${size}" stroke="rgba(15,23,42,0.12)" />`;
    svg += `<line x1="0" y1="${i * CS}" x2="${size}" y2="${i * CS}" stroke="rgba(15,23,42,0.12)" />`;
  }

  svg += `<rect x="${CS}" y="${CS}" width="${CS * 2}" height="${CS * 2}" fill="rgba(139,115,56,0.04)" />`;

  for (let ri = 0; ri < 4; ri++) {
    for (let ci = 0; ci < 4; ci++) {
      const si = layout[ri][ci];
      if (si < 0) continue;
      const x = ci * CS;
      const y = ri * CS;
      const isLagna = si === lagnaSign;
      const planets = occ[si] ?? [];
      const house = ((si - lagnaSign + 12) % 12) + 1;

      svg += `<text x="${x + 6}" y="${y + CS * 0.18}" font-size="${CS * 0.15}" fill="${isLagna ? "#1e3a5f" : "#475569"}" font-family="monospace" font-weight="${isLagna ? 700 : 400}">${RASHI_SHORT[si]}</text>`;
      svg += `<text x="${x + CS - 5}" y="${y + CS * 0.18}" text-anchor="end" font-size="${CS * 0.11}" fill="rgba(71,85,105,0.5)" font-family="monospace">${house}</text>`;

      if (planets.length) {
        const lines: string[][] = [];
        const perRow = 2;
        for (let j = 0; j < planets.length; j += perRow) lines.push(planets.slice(j, j + perRow));
        lines.forEach((row, ri2) => {
          svg += `<text x="${x + CS / 2}" y="${y + CS * 0.55 + ri2 * (CS * 0.17)}" text-anchor="middle" font-size="${CS * 0.155}" fill="#0f172a" font-family="monospace" font-weight="600">${row.join(" ")}</text>`;
        });
      }

      if (isLagna) {
        svg += `<text x="${x + CS / 2}" y="${y + CS - 7}" text-anchor="middle" font-size="${CS * 0.12}" fill="#1e3a5f" font-family="monospace" letter-spacing="0.06em">LAGNA</text>`;
      }
    }
  }

  svg += `</svg>`;
  return svg;
}

function printPage(chart: ChartData): string {
  const now = new Date().toISOString().slice(0, 10);
  const name = chart.meta?.name ?? "Chart";
  const signs = chart.vargas?.D1?.signs ?? chart.natalSign ?? {};
  const chartSVG = renderSouthChartSVG(signs, 340);

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>VedicAstro – ${name}</title>
  <style>
    @media print {
      @page { margin: 0.6in; size: A4; }
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Georgia, serif;
      color: #0f172a;
      background: #ffffff;
      padding: 32px;
      line-height: 1.6;
    }
    .header {
      text-align: center;
      margin-bottom: 32px;
      border-bottom: 2px solid #1e3a5f;
      padding-bottom: 20px;
    }
    .header h1 { font-size: 24px; font-weight: 700; color: #1e3a5f; margin-bottom: 4px; }
    .header .subtitle { font-size: 13px; color: #475569; }
    .chart-grid {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 28px;
      margin-bottom: 32px;
      align-items: start;
    }
    .chart-grid svg { display: block; }
    .info-box {
      font-size: 12px;
      color: #475569;
      background: #f8f5f0;
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 14px;
    }
    .info-box span { display: block; margin-bottom: 3px; }
    .info-box .label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }
    .info-box .value { font-weight: 600; color: #0f172a; }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-bottom: 32px;
    }
    th {
      text-align: left;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #475569;
      border-bottom: 2px solid #1e3a5f;
      padding: 8px 10px;
    }
    td {
      padding: 7px 10px;
      border-bottom: 0.5px solid rgba(15, 23, 42, 0.1);
    }
    .footer {
      text-align: center;
      font-size: 10px;
      color: #64748b;
      border-top: 0.5px solid rgba(15, 23, 42, 0.1);
      padding-top: 16px;
      margin-top: 16px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>${name}</h1>
    <div class="subtitle">
      ${chart.meta?.birth_datetime ? `Born ${chart.meta.birth_datetime} · ` : ""}
      ${chart.meta?.birth_lat != null ? `Lat ${chart.meta.birth_lat.toFixed(4)}° · ` : ""}
      ${chart.meta?.birth_lon != null ? `Lon ${chart.meta.birth_lon.toFixed(4)}° · ` : ""}
      Ayanāṁśa: ${chart.ayanamsa}
    </div>
  </div>

  <div class="chart-grid">
    ${chartSVG}

    <div>
      <div class="info-box">
        <span class="label">Lagna</span>
        <span class="value">${chart.lagna.rashi} · ${chart.lagna.degLabel ?? ""}</span>
        <span class="value" style="font-weight:400;">${chart.lagna.nakshatra} Pada ${chart.lagna.pada}</span>
      </div>

      <div class="info-box">
        <span class="label">Chart Summary</span>
        <span class="value">${chart.ayanamsa} ayanamsa</span>
        <span class="value" style="font-weight:400;">Engine: ${chart.meta?.engine ?? "Swiss Ephemeris"} · JD ${chart.jd.toFixed(4)}</span>
        ${chart.dashas?.current != null ? '<span class="value" style="font-weight:400;">Dasha: ' + JSON.stringify(chart.dashas.current) + '</span>' : ''}
      </div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Planet</th>
        <th>Rāśi</th>
        <th>Nakṣatra</th>
        <th>Pada</th>
        <th>Deg</th>
        <th>State</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="font-weight:600; color:#1e3a5f;">Lagna</td>
        <td>${chart.lagna.rashi}</td>
        <td>${chart.lagna.nakshatra}</td>
        <td>${chart.lagna.pada}</td>
        <td style="font-family:monospace;">${chart.lagna.degLabel ?? ""}</td>
        <td></td>
      </tr>
      ${chart.planets
        .map(
          (p) => `
      <tr>
        <td style="font-weight:600;">${p.planet}</td>
        <td>${p.rashi}</td>
        <td>${p.nakshatra}</td>
        <td>${p.pada}</td>
        <td style="font-family:monospace;">${p.degLabel ?? ""}</td>
        <td>
          ${p.dignity && p.dignity !== "neutral" ? p.dignity : ""}
          ${p.retro ? " ℞" : ""}
          ${p.combust ? " ☌" : ""}
        </td>
      </tr>`,
        )
        .join("")}
    </tbody>
  </table>

  ${chart.vargas ? `
  <h3 style="font-size:14px; color:#1e3a5f; margin-bottom:10px; font-weight:600;">Vargas Available</h3>
  <table>
    <thead><tr><th>Varga</th><th>Name</th><th>Lagna Sign</th></tr></thead>
    <tbody>
      ${Object.entries(chart.vargas)
        .map(
          ([k, v]) => `
      <tr>
        <td style="font-weight:600;">${k}</td>
        <td>${v.name}</td>
        <td>${RASHIS[v.signs.Lagna ?? 0]}</td>
      </tr>`,
        )
        .join("")}
    </tbody>
  </table>
  ` : ""}

  <div class="footer">
    Generated on ${now} · VedicAstro · Swiss Ephemeris · Lahiri
  </div>
</body>
</html>`;
}

export function ExportPDFButton({ chart }: { chart: ChartData }) {
  const [printing, setPrinting] = useState(false);

  const handleExport = () => {
    setPrinting(true);

    try {
      const html = printPage(chart);
      const w = window.open("", "_blank", "popup,width=900,height=700");
      if (!w) {
        setPrinting(false);
        return;
      }
      w.document.write(html);
      w.document.close();
      w.focus();
      w.onload = () => {
        w.print();
        setPrinting(false);
      };
      setTimeout(() => {
        if (printing) setPrinting(false);
      }, 3000);
    } catch {
      setPrinting(false);
    }
  };

  return (
    <Button
      variant="ghost"
      onClick={handleExport}
      disabled={printing}
      className="text-xs"
    >
      <Download className="w-4 h-4" />
      {printing ? "Printing..." : "Export PDF"}
    </Button>
  );
}
