"use client";

import { useEffect, useState } from "react";

const LOADING_PHRASES = [
  "Contemplating the stars…",
  "Consulting the Panchang…",
  "Divining the dasha…",
  "Aligning with Jupiter's counsel…",
  "Charting the nakshatras…",
  "Weighing the Ashtakavarga…",
  "Reading the Kundali…",
  "Tracing planetary aspects…",
  "Honoring Saturn's patience…",
  "Measuring the bhavas…",
  "Summoning the Swiss Ephemeris…",
  "Consulting Maharshi Parasara…",
  "Untangling the Rahu-Ketu axis…",
  "Casting the Navamsa…",
  "Counting bindus in the Ashtakavarga…",
];

/** Rotating, mildly playful busy-indicator text — replaces a single static
 * "computing…" string so a slow request doesn't read as a hung one. */
export function LoadingPhrase({ intervalMs = 1600 }: { intervalMs?: number }) {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * LOADING_PHRASES.length));

  useEffect(() => {
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % LOADING_PHRASES.length);
    }, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return <span>{LOADING_PHRASES[index]}</span>;
}
