import type { Metadata } from "next";
import { Fraunces, Sora, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";
import { getSession } from "@/lib/auth/session";

// Deliberate type system (not the default): Fraunces — an optical serif — for
// display/headings carries the cultural, premium character; Sora for clean UI
// body; JetBrains Mono for data/labels. Mirrors the Muhurta module's identity.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz"],
});
const sora = Sora({ variable: "--font-geist-sans", subsets: ["latin"], weight: ["300", "400", "500", "600"] });
const jetbrains = JetBrains_Mono({ variable: "--font-geist-mono", subsets: ["latin"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "VedicShastra AI — Sidereal Vedic Astrology",
  description:
    "Premium, accurate, rule-based Vedic astrology. Swiss-Ephemeris charts, divisional vargas, dashas and ashtakavarga — computed with classical fidelity.",
};

// Apply persisted theme before paint to avoid a flash.
const themeScript = `(function(){try{var t=localStorage.getItem('va-theme');if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark');}catch(e){}})();`;

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await getSession().catch(() => null);

  return (
    <html lang="en" className={`${fraunces.variable} ${sora.variable} ${jetbrains.variable} h-full antialiased`} data-font suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full flex flex-col">
        <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2 focus:bg-accent focus:text-accent-fg focus:rounded-lg focus:text-sm focus:font-medium">Skip to content</a>
        <SiteHeader signedIn={!!session} role={session?.role} />
        <main id="main-content" className="flex-1" tabIndex={-1}>{children}</main>
        <footer className="border-t border-hairline px-6 py-8 text-center text-xs text-text-muted">
          VedicShastra AI · Sidereal (Nirayana) · Lahiri ayanāṁśa · Swiss Ephemeris.
          Predictions are rule-based and for reflection, not deterministic fate.
        </footer>
      </body>
    </html>
  );
}
