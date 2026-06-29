"use client";

import { motion } from "motion/react";
import { BookOpen, ArrowRight } from "lucide-react";
import Link from "next/link";

interface Book {
  id: string;
  title: string;
  author: string;
  era: string;
  description: string;
  focus: string;
  href?: string;
}

const BOOKS: Book[] = [
  {
    id: "bpHS",
    title: "Bṛhat Parāśara Horā Śāstra",
    author: "Maharishi Parashara",
    era: "~7th–8th c. CE",
    description: "The foundational treatise on natal astrology. Comprehensive coverage of planets, signs, houses, dashas, yogas and remedial measures.",
    focus: "Natal chart, Dasha, Yogas",
    href: "#",
  },
  {
    id: "js",
    title: "Jaimini Sūtras",
    author: "Maharishi Jaimini",
    era: "~4th c. BCE – 4th c. CE",
    description: "Aphoristic work outlining Jaimini system: Chara dasha, karakas, arudha, special lagnas and longevity methods.",
    focus: "Jaimini, Chara Dasha",
    href: "/learn/jaimini",
  },
  {
    id: "jp",
    title: "Jātaka Pārijāta",
    author: "Vaidyanatha Dikshita",
    era: "~15th c. CE",
    description: "Elegant consolidation of earlier works with clear rules for judgment, strength calculation and predictive techniques.",
    focus: "Judgment, Strength",
    href: "#",
  },
  {
    id: "hs",
    title: "Horā Sāra",
    author: "Prithuyasas",
    era: "~6th c. CE",
    description: "Concise yet profound text on horoscopic interpretation, emphasizing planetary strength and house results.",
    focus: "Interpretation",
    href: "#",
  },
  {
    id: "sp",
    title: "Sārāvalī",
    author: "Kalyana Varma",
    era: "~10th c. CE",
    description: "Extensive compilation covering all major topics with additional verses on female horoscopy and lost works.",
    focus: "Compilation, Female charts",
    href: "#",
  },
  {
    id: "ph",
    title: "Phaladīpikā",
    author: "Mantreshwara",
    era: "~13th c. CE",
    description: "Practical manual prized for its clarity on dashas, transits, ashtakavarga and everyday predictive methods.",
    focus: "Dasha, Gochar, Ashtakavarga",
    href: "#",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
};

export default function LearnPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-10 lg:py-14">
      {/* Hero */}
      <div className="max-w-3xl mb-12">
        <div className="inline-flex items-center gap-2 rounded-full border border-hairline px-3 py-1 text-xs tracking-[0.08em] text-text-muted mb-4">
          <BookOpen className="w-3.5 h-3.5" /> ŚĀSTRA SAṄGRAHA
        </div>
        <h1 className="font-display text-5xl lg:text-6xl tracking-[-0.02em] text-balance mb-4">
          The classical library
        </h1>
        <p className="text-lg text-text-muted max-w-2xl">
          Timeless works that form the living foundation of Jyotiṣa. Each text is a complete system — study them in order, return often.
        </p>
      </div>

      {/* Book Library Grid */}
      <section aria-labelledby="library-heading" className="mb-16">
        <div className="flex items-end justify-between mb-6">
          <div>
            <h2 id="library-heading" className="font-display text-3xl tracking-[-0.01em]">Book Library</h2>
            <p className="text-sm text-text-muted mt-1">Core canonical texts • 6 shown • more added continuously</p>
          </div>
          <Link
            href="#"
            className="hidden sm:inline-flex items-center gap-1.5 text-sm text-accent hover:text-accent-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-lg px-3 py-1.5"
          >
            Browse full corpus <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {BOOKS.map((book) => (
            <motion.article
              key={book.id}
              variants={cardVariants}
              whileHover={{ y: -2 }}
              className="group flex flex-col rounded-2xl border border-hairline bg-card p-7 transition-colors hover:border-accent/40 focus-within:border-accent/40"
            >
              <div className="flex-1">
                <div className="flex items-start justify-between gap-4">
                  <h3 className="font-display text-2xl tracking-[-0.01em] leading-tight pr-2">{book.title}</h3>
                  <div className="shrink-0 text-[10px] font-mono uppercase tracking-[0.12em] text-text-muted pt-1.5">{book.era}</div>
                </div>
                <div className="mt-1.5 text-sm text-accent font-medium">{book.author}</div>

                <p className="mt-4 text-[15px] leading-relaxed text-text-muted">{book.description}</p>
              </div>

              <div className="mt-6 pt-5 border-t border-hairline flex items-center justify-between text-sm">
                <span className="font-mono text-xs uppercase tracking-[0.08em] text-text-muted">{book.focus}</span>
                {book.href ? (
                  <Link
                    href={book.href}
                    className="inline-flex items-center gap-1 text-accent hover:text-accent-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-md px-2 py-0.5 -mr-2"
                    aria-label={`Open ${book.title}`}
                  >
                    Open <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                ) : (
                  <span className="text-xs text-text-muted">Coming soon</span>
                )}
              </div>
            </motion.article>
          ))}
        </motion.div>
      </section>

      {/* Quick Explorers */}
      <section aria-labelledby="explorers-heading">
        <h2 id="explorers-heading" className="font-display text-3xl tracking-[-0.01em] mb-6">Interactive Explorers</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
          <Link
            href="/learn/rashis"
            className="flex items-center justify-between rounded-2xl border border-hairline bg-card px-6 py-5 text-lg hover:border-accent/40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 group"
          >
            <span>Rāśi Explorer</span>
            <ArrowRight className="w-5 h-5 text-accent group-hover:translate-x-0.5 transition" />
          </Link>
          <Link
            href="/learn/nakshatras"
            className="flex items-center justify-between rounded-2xl border border-hairline bg-card px-6 py-5 text-lg hover:border-accent/40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 group"
          >
            <span>Nakṣatra Explorer</span>
            <ArrowRight className="w-5 h-5 text-accent group-hover:translate-x-0.5 transition" />
          </Link>
        </div>
      </section>
    </div>
  );
}
