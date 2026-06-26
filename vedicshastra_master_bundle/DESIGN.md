# VedicShastra AI – Design System & UI Blueprint (Tailwind v4)

This is the **single source of truth** for all UI generation and development in VedicShastra AI.

**Every AI agent, developer, or tool must read this file before creating or modifying any UI component.**

## 1. Brand Identity

VedicShastra AI is a **premium, modern, trustworthy Vedic Astrology platform**.

The design must feel:
- Elegant and calm
- Insightful and professional
- Culturally respectful (subtle Vedic influence, never kitschy)
- Clear and accessible

### Color Palette (Tailwind v4 CSS Variables)

Add this to `src/app/globals.css`:

```css
@theme {
  --color-primary: #1E3A5F;        /* Deep Royal Indigo */
  --color-accent: #C5A46E;         /* Warm Gold / Saffron */
  --color-background: #F8F5F0;     /* Warm Off-White */
  --color-card: #FFFFFF;
  --color-text-main: #0F172A;
  --color-text-muted: #475569;
  --color-success: #15803D;
  --color-warning: #B45309;
}
```

**Usage Rules**:
- Primary actions: `bg-primary text-white`
- Accent highlights: `text-accent` or `border-accent`
- Cards: `bg-card` with subtle shadows
- Never use pure black or arbitrary hex colors.

### Typography
- Headings: `font-sans font-semibold tracking-tight`
- Body: `text-[15px] leading-relaxed`
- Sanskrit/technical terms: Use medium weight with slight tracking

### Spacing & Layout (Strict)
- Main container: `max-w-7xl mx-auto px-6`
- Section padding: `py-20` (desktop), `py-14` (mobile)
- Cards: `p-8 rounded-2xl`
- Consistent gaps: `gap-8`

## 2. Core Component Blueprints

### Primary Button
```tsx
className="bg-primary hover:bg-primary/90 text-white font-medium px-6 py-3 rounded-xl transition-all active:scale-[0.985]"
```

### Card (Prediction / Chart / Data)
```tsx
className="bg-card border border-neutral-200/60 rounded-2xl shadow-sm hover:shadow-md transition-shadow p-8"
```

### Interactive Chart Container
```tsx
className="bg-card rounded-3xl p-6 border border-neutral-200/50"
```

## 3. Animation Rules (Framer Motion)

- All meaningful motion must use **Framer Motion**.
- Keep animations **subtle and purposeful**.
- Chart interactions: Smooth hover + gentle scale.
- Prediction reveals: Staggered entrance (0.05s delay).
- All interactive elements: `transition-all duration-200`.

**Example**:
```tsx
<motion.div whileHover={{ scale: 1.01 }} transition={{ duration: 0.2 }}>
```

## 4. Strict Constraints for AI Tools

1. **Never** use arbitrary Tailwind values (e.g. `bg-[#123456]` or `rounded-[17px]`).
2. All colors must come from the defined CSS variables.
3. Follow component blueprints exactly.
4. Prioritize **clarity and elegance** over decoration.
5. Support both North Indian and South Indian chart styles elegantly.
6. Dark mode support is mandatory from day one.

## 5. AI Generation Instruction

When prompting any AI (Claude Code, ruflo agents, 21st.dev Magic, etc.):

> "You must first read and strictly follow every rule in DESIGN.md. Use only the defined colors, spacing, typography, and component patterns. Prioritize elegance, clarity, and consistency."

## 6. Key Screens Character

- **Landing**: Premium, calm, trustworthy
- **Dashboard**: Clear, insightful, calm
- **Horoscope Chart Viewer**: The hero experience — highly interactive and elegant
- **Prediction Results**: Balanced, respectful, with smooth feedback UI
- **Admin Panel**: Professional and powerful

---

**Last Updated**: 24 June 2026
**Version**: 1.0