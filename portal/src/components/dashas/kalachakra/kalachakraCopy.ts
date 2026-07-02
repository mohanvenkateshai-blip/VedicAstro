import type { KalachakraLeapInfo } from "@/lib/types";

type LeapType = KalachakraLeapInfo["type"];

interface LeapStyle {
  shortLabel: string;
  colorClass: string; // text color
  bgClass: string; // badge/banner background
  borderClass: string;
  explanation: string;
}

export const LEAP_STYLES: Record<LeapType, LeapStyle> = {
  frog_leap: {
    shortLabel: "Frog Leap",
    colorClass: "text-amber-500",
    bgClass: "bg-amber-500/10",
    borderClass: "border-amber-500/40",
    explanation:
      "The dasha skips backward over one sign (Mandooki Gati). Classically this marks a sudden, compressed detour — a short revisiting of themes from a sign you'd already moved past, before the sequence continues.",
  },
  lions_leap: {
    shortLabel: "Lion Leap",
    colorClass: "text-danger",
    bgClass: "bg-danger/10",
    borderClass: "border-danger/40",
    explanation:
      "The dasha jumps to the 5th or 9th sign from where it stood (Simhavalokana Gati) — a large, trine-position leap. Classically likened to a lion glancing back before a decisive move: a period of abrupt, elevated change.",
  },
  monkey_leap: {
    shortLabel: "Monkey Leap",
    colorClass: "text-violet-400",
    bgClass: "bg-violet-500/10",
    borderClass: "border-violet-500/40",
    explanation:
      "The dasha moves backward by one sign, against its expected direction (Markati Gati). The most common of the three Gatis — classically associated with restlessness, a temporary setback, or circling back to unfinished business.",
  },
};

export function leapStyle(type: LeapType): LeapStyle {
  return LEAP_STYLES[type];
}
