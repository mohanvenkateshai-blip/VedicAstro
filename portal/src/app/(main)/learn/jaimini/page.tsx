import { redirect } from "next/navigation";

/**
 * Jaimini has a dedicated nav link but uses the same structured book reader as all classics.
 * The old node-only view showed "0 nodes" on production; structured + full markdown is authoritative.
 */
export default function JaiminiRedirectPage() {
  redirect("/learn/Jaimini_Sutras");
}
