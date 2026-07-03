import { Undo2, SkipBack, Zap, type LucideIcon } from "lucide-react";
import type { KalachakraLeapInfo, KalachakraLeapStrength } from "@/lib/types";

type LeapType = KalachakraLeapInfo["type"];

interface LeapStyle {
  shortLabel: string;
  icon: LucideIcon;
  colorClass: string; // text color
  bgClass: string; // badge/banner background (soft)
  borderClass: string; // soft border
  solidClass: string; // strong background for the left-border accent bar
  explanation: string;
  classicEffects: string;
  positivePotential: string;
}

export const LEAP_STYLES: Record<LeapType, LeapStyle> = {
  frog_leap: {
    shortLabel: "Frog Leap",
    icon: SkipBack,
    colorClass: "text-amber-500",
    bgClass: "bg-amber-500/10",
    borderClass: "border-amber-500/40",
    solidClass: "bg-amber-500",
    explanation:
      "The dasha skips backward over one sign (Mandooki Gati) — a sudden, compressed detour, briefly revisiting a sign already passed before the sequence continues.",
    classicEffects: "Distress to elders, trouble from enemies or weapons.",
    positivePotential: "Sudden breakthrough after stagnation; a major lifestyle transformation.",
  },
  lions_leap: {
    shortLabel: "Lion Leap",
    icon: Zap,
    colorClass: "text-danger",
    bgClass: "bg-danger/10",
    borderClass: "border-danger/40",
    solidClass: "bg-danger",
    explanation:
      "The dasha jumps to the 5th or 9th sign from where it stood (Simhavalokana Gati) — a large, trine-position leap likened to a lion glancing back before a decisive move.",
    classicEffects: "Sudden status change, fear, accidents.",
    positivePotential: "Dramatic elevation, spiritual initiation, or a major life pivot that ultimately benefits the native.",
  },
  monkey_leap: {
    shortLabel: "Monkey Leap",
    icon: Undo2,
    colorClass: "text-violet-400",
    bgClass: "bg-violet-500/10",
    borderClass: "border-violet-500/40",
    solidClass: "bg-violet-500",
    explanation:
      "The dasha moves backward by one sign, against its expected direction (Markati Gati) — the most common of the three Gatis.",
    classicEffects: "Loss, reversal, distress to father.",
    positivePotential: "A necessary correction leading to greater long-term stability, or a return to the true path.",
  },
};

export function leapStyle(type: LeapType): LeapStyle {
  return LEAP_STYLES[type];
}

interface StrengthStyle {
  label: string;
  colorClass: string;
  bgClass: string;
  dotClass: string;
}

const STRENGTH_STYLES: Record<KalachakraLeapStrength["band"], StrengthStyle> = {
  strong: { label: "Positive potential", colorClass: "text-success", bgClass: "bg-success/10", dotClass: "bg-success" },
  good: { label: "Positive potential", colorClass: "text-teal-400", bgClass: "bg-teal-400/10", dotClass: "bg-teal-400" },
  neutral: { label: "Mixed", colorClass: "text-accent", bgClass: "bg-accent/10", dotClass: "bg-accent" },
  weak: { label: "Challenging", colorClass: "text-danger", bgClass: "bg-danger/10", dotClass: "bg-danger" },
};

export function strengthStyle(strength: KalachakraLeapStrength): StrengthStyle {
  return STRENGTH_STYLES[strength.band];
}
