import { ButtonLink } from "@/components/ui/Button";
import { Card, CardLabel } from "@/components/ui/Card";
import { getHealth } from "@/lib/cvce";
import { Sparkles, Compass, ScrollText, Activity } from "lucide-react";

export default async function Home() {
  const health = await getHealth();

  return (
    <>
      {/* Hero */}
      <section className="bg-aurora">
        <div className="mx-auto max-w-7xl px-6 py-24 md:py-32">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-hairline px-3 py-1 text-xs text-text-muted">
              <Sparkles size={13} className="text-accent" />
              Sidereal · Swiss Ephemeris · classical rules
            </span>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight md:text-6xl">
              Vedic astrology with
              <span className="text-accent"> uncompromising accuracy.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-text-muted">
              Research-grade sidereal computation — divisional vargas, Vimśottarī
              daśās, ashtakavarga and shadbala — rendered in elegant, interactive
              charts. Grounded in the classical texts, never sugar-coated.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <ButtonLink href="/chart" variant="accent">
                Cast your chart
              </ButtonLink>
              <ButtonLink href="/chart?name=Mohan&date=1975-04-22&time=19:15&lat=12.2958&lon=76.6394&tz=5.5&place=Mysore" variant="ghost">
                See a sample
              </ButtonLink>
            </div>
            {health && (
              <p className="mt-6 inline-flex items-center gap-2 text-xs text-text-muted">
                <span className="h-2 w-2 rounded-full bg-success" />
                Calculation engine online — {health.engine}
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Feature triptych */}
      <section className="mx-auto max-w-7xl px-6 pb-24">
        <div className="grid gap-6 md:grid-cols-3">
          {[
            {
              icon: Compass,
              label: "Precision core",
              title: "Swiss Ephemeris, Lahiri sidereal",
              body: "Every position validated against an independent ephemeris. D1–D60 vargas, true planetary states, retrogression and combustion.",
            },
            {
              icon: ScrollText,
              label: "Classical fidelity",
              title: "Rules from the śāstras",
              body: "Yogas, ashtakavarga and daśā logic drawn from Parāśara, Phaladīpikā and the classical corpus — traceable, not invented.",
            },
            {
              icon: Activity,
              label: "Living charts",
              title: "Interactive North & South",
              body: "Toggle traditions, switch divisional charts, inspect every planet. Charts you can read, not just look at.",
            },
          ].map(({ icon: Icon, label, title, body }) => (
            <Card key={title} className="p-8">
              <Icon size={22} className="text-accent" />
              <div className="mt-5">
                <CardLabel>{label}</CardLabel>
                <h3 className="mt-1.5 text-lg font-semibold tracking-tight">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-muted">{body}</p>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </>
  );
}
