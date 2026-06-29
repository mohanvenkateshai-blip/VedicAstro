import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Learn — Vedic Shastra Library | VedicShastra AI",
  description: "Classical Jyotisha texts, rashi and nakshatra explorers. Study the foundational works of Vedic astrology in a focused, premium environment.",
};

export default function LearnLayout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-[calc(100vh-4rem)]">{children}</div>;
}
