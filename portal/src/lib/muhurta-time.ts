export type MuhurtaWindowTime = number | string;

/** Format either a legacy decimal hour or the canonical CVCE HH:MM:SS value. */
export function formatMuhurtaWindowTime(value: MuhurtaWindowTime): string {
  if (typeof value === "string") {
    const match = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(value.trim());
    if (!match) return "Unavailable";

    const hours = Number(match[1]);
    const minutes = Number(match[2]);
    const seconds = match[3] === undefined ? 0 : Number(match[3]);
    if (hours > 23 || minutes > 59 || seconds > 59) return "Unavailable";
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
  }

  if (!Number.isFinite(value)) return "Unavailable";
  const totalMinutes = Math.round(value * 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = ((totalMinutes % 60) + 60) % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}
