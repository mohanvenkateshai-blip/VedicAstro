import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Muhūrta — VedicShastra AI",
  description: "Native CVCE-backed electional astrology inside the chart workspace.",
};

export default function MuhurtaPage() {
  redirect("/chart/muhurta");
}
