import type {
  KalachakraLeapInfo,
  KalachakraMoonNavamsaPoint,
  KalachakraNode,
  KalachakraSignInterpretation,
} from "@/lib/types";
import { leapStyle } from "./kalachakraCopy";

const PLANET_DOMAIN: Record<string, string> = {
  Sun: "authority, vitality, and the self",
  Moon: "the mind, the mother, and emotional life",
  Mars: "courage, property, and siblings",
  Mercury: "intellect, trade, and communication",
  Jupiter: "wealth, wisdom, children, and dharma",
  Venus: "relationships, comfort, and the arts",
  Saturn: "discipline, longevity, and delay",
  Rahu: "ambition and the unconventional",
  Ketu: "detachment and quiet release",
};

function domainPhrase(planets: string[]): string {
  if (planets.length === 0) return "";
  const phrases = planets.map((p) => PLANET_DOMAIN[p] ?? p);
  return phrases.join(" and ");
}

function listJoin(items: string[]): string {
  if (items.length === 0) return "";
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

/** Deterministic 0..n-1 pick so the same period always reads the same way on
 * re-render, but different signs/levels don't all sound identical. */
function pick<T>(options: T[], seed: number): T {
  return options[Math.abs(seed) % options.length];
}

function openingLine(
  node: KalachakraNode,
  isDeha: boolean,
  isJeeva: boolean,
  isMoonNavamsa: boolean,
): string {
  const level = node.level === 1 ? "Mahadasha" : node.level === 2 ? "Antardasha" : "Pratyantardasha";
  if (isDeha) {
    return `This ${level} falls in ${node.sign} — the Deha Rasi, the very seed-point this whole 86-year cycle springs from. Whatever unfolds here reaches straight into the body, the health, and the raw vitality of this life.`;
  }
  if (isJeeva) {
    return `This ${level} falls in ${node.sign} — the Jeeva Rasi, the far shore of the cycle where the wheel's story completes itself. Its themes run closer to spirit and inner life than to worldly circumstance.`;
  }
  if (isMoonNavamsa) {
    return `This ${level} runs through ${node.sign} — the sign the Moon itself occupies in the Navamsa, a quietly sensitive point PVR Rao's tradition treats with the same weight as Deha and Jeeva.`;
  }
  return pick(
    [
      `This ${level} runs through ${node.sign}.`,
      `The chart now turns to ${node.sign} for this ${level}.`,
      `${node.sign} takes the stage for this ${level}.`,
    ],
    node.signIndex + node.level,
  );
}

function argalaNarrative(interp: KalachakraSignInterpretation): string {
  const { argala, sign } = interp;
  if (argala.verdict === "boosted" && argala.ownLordPresent) {
    return pick(
      [
        `${sign} draws real strength here — its own lord stands guard over the house, unchallenged by anything working against it.`,
        `There's a quiet sturdiness to this sign: ${sign}'s own ruling planet holds ground right where it matters, with no serious opposition in sight.`,
      ],
      interp.signIndex,
    );
  }
  if (argala.verdict === "boosted") {
    return `Support gathers around this house — ${listJoin(argala.givers)} reach in with Argala, and nothing of consequence pulls against it.`;
  }
  if (argala.verdict === "obstructed" && argala.maleficOccupant.length > 0) {
    return `A harder edge shows here: ${listJoin(argala.maleficOccupant)} sit directly in ${sign}, and no supporting hand reaches in to soften the effect.`;
  }
  if (argala.verdict === "obstructed") {
    return `More is working to block this house's affairs than to support them — ${listJoin(argala.obstructors)} outweigh whatever help is on offer.`;
  }
  return `${sign} sits in relatively open territory here — neither strongly propped up nor pulled down, so its story will largely be written by what else is active in the chart at the time.`;
}

function specialGiverNarrative(interp: KalachakraSignInterpretation): string | null {
  const parts: string[] = [];
  if (interp.yogakaraka) {
    parts.push(
      `${interp.yogakaraka}, the Yogakaraka for this chart, has a hand in this period too — the kind of placement classical texts associate with status rising alongside the tests it brings.`,
    );
  }
  if (interp.karakas.length > 0) {
    parts.push(`This house also carries the natural signification of ${domainPhrase(interp.karakas)}.`);
  }
  if (interp.isLagnaLordSign) {
    parts.push(`Notably, this is also where the Lagna lord itself sits — the period touches the native's own core, not just a peripheral house.`);
  }
  return parts.length ? parts.join(" ") : null;
}

function leapNarrative(leap: KalachakraLeapInfo): string[] {
  const style = leapStyle(leap.type);
  const out: string[] = [
    `The path into this period wasn't a simple step forward — it arrived by a ${style.shortLabel} (${style.explanation.split(" — ")[1] ?? style.explanation})`,
  ];
  if (leap.strength) {
    const verdictPhrase =
      leap.strength.verdict === "positive_potential"
        ? "and the Ashtakavarga strength behind this sign leans favorable, which tends to soften a leap's rougher classical edge"
        : leap.strength.verdict === "challenging"
          ? "and the Ashtakavarga strength behind this sign runs thin, which tends to sharpen a leap's more difficult classical effects"
          : "with mixed Ashtakavarga strength behind it — neither clearly cushioning nor sharpening the leap's effects";
    out.push(`Its bindu count ${verdictPhrase}.`);
  }
  if (leap.travelDirection) {
    const { favorable, unfavorable } = leap.travelDirection;
    const bits: string[] = [];
    if (favorable.length) bits.push(`${listJoin(favorable)} is classically favorable for travel or new beginnings`);
    if (unfavorable.length) bits.push(`${listJoin(unfavorable)} is best avoided for the same`);
    if (bits.length) {
      out.push(`Parasara's own tradition names a direction for a leap like this one: ${bits.join(", while ")}.`);
    }
  }
  return out;
}

function closingLine(interp: KalachakraSignInterpretation, leap: KalachakraLeapInfo | null): string {
  const boosted = interp.argala.verdict === "boosted";
  const obstructed = interp.argala.verdict === "obstructed";
  if (leap && leap.type === "lions_leap" && boosted) {
    return "On balance, this reads as a genuine high point — a dramatic turn that this chart is well-placed to carry.";
  }
  if (obstructed) {
    return "On balance, this period asks for patience and care rather than big swings.";
  }
  if (boosted) {
    return "On balance, this looks like a supportive stretch — a reasonable window to lean into its themes.";
  }
  return "On balance, this is a steadier, more ordinary stretch — its outcome will hinge more on the moment's transits than on this period's own signature.";
}

/**
 * Storytelling narrative for one MD/AD/PD period — an ordered list of
 * paragraphs meant to be rendered sequentially, not a single blob.
 */
export function narratePeriod(
  node: KalachakraNode,
  signInterpretations: KalachakraSignInterpretation[] | null | undefined,
  moonNavamsaPoint: KalachakraMoonNavamsaPoint | null | undefined,
  dehaRasi: string | undefined,
  jeevaRasi: string | undefined,
): string[] {
  const interp = signInterpretations?.find((s) => s.signIndex === node.signIndex);
  const isDeha = node.sign === dehaRasi;
  const isJeeva = node.sign === jeevaRasi;
  const isMoonNavamsa = !!moonNavamsaPoint && moonNavamsaPoint.signIndex === node.signIndex && !isDeha && !isJeeva;

  const lines: string[] = [openingLine(node, isDeha, isJeeva, isMoonNavamsa)];

  if (interp) {
    lines.push(argalaNarrative(interp));
    const special = specialGiverNarrative(interp);
    if (special) lines.push(special);
  }

  if (node.leapFromPrevious) {
    lines.push(...leapNarrative(node.leapFromPrevious));
  }

  if (interp) {
    lines.push(closingLine(interp, node.leapFromPrevious));
  }

  return lines;
}

/** Condensed 1-sentence teaser for the currently-active period, for the
 * CurrentStateWidget — the Argala line only, trimmed to read standalone.
 * Takes just a signIndex (not a full KalachakraNode) so it works directly
 * with currentLadder rows too. */
export function narrateTeaser(
  signIndex: number,
  signInterpretations: KalachakraSignInterpretation[] | null | undefined,
): string | null {
  const interp = signInterpretations?.find((s) => s.signIndex === signIndex);
  if (!interp) return null;
  return argalaNarrative(interp);
}
