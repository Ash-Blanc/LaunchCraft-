import type { CSSProperties } from "react";
import type { Brand, VisualDirection } from "@/types/api";

export interface StoreTheme {
  display: string;
  body: string;
  headingWeight: number;
  /** Tailwind classes, all container-query based so the preview behaves like a real viewport. */
  grid: string;
  imageFrame: string;
  imageAspect: string;
  card: string;
  hero: "split" | "arch" | "block" | "sticker" | "quiet";
  label: string;
}

const NEWSREADER = '"Newsreader Variable", Georgia, serif';
const YOUNG = '"Young Serif", Georgia, serif';
const BRICOLAGE = '"Bricolage Grotesque Variable", ui-sans-serif, system-ui, sans-serif';
const PUBLIC = '"Public Sans Variable", ui-sans-serif, system-ui, sans-serif';

export const THEMES: Record<VisualDirection, StoreTheme> = {
  editorial: {
    display: NEWSREADER, body: PUBLIC, headingWeight: 400,
    grid: "grid grid-cols-1 gap-x-6 gap-y-10 @md:grid-cols-2 @3xl:grid-cols-3",
    imageFrame: "", imageAspect: "aspect-[4/5]", card: "", hero: "split",
    label: "Editorial: a serif masthead and a magazine-style grid",
  },
  botanical: {
    display: YOUNG, body: PUBLIC, headingWeight: 400,
    grid: "grid grid-cols-1 gap-x-8 gap-y-12 @md:grid-cols-2",
    imageFrame: "rounded-t-[999px]", imageAspect: "aspect-[4/5]", card: "text-center", hero: "arch",
    label: "Botanical: soft serif type and arched images",
  },
  workshop: {
    display: BRICOLAGE, body: PUBLIC, headingWeight: 750,
    grid: "grid grid-cols-2 border-l border-t border-[color:var(--s-rule)] @3xl:grid-cols-4",
    imageFrame: "", imageAspect: "aspect-square",
    card: "border-r border-b border-[color:var(--s-rule)] p-3", hero: "block",
    label: "Workshop: bold grotesque type and a dense catalogue grid",
  },
  playful: {
    display: BRICOLAGE, body: PUBLIC, headingWeight: 650,
    grid: "grid grid-cols-1 gap-6 @md:grid-cols-2 @3xl:grid-cols-3",
    imageFrame: "rounded-[28px]", imageAspect: "aspect-square", card: "", hero: "sticker",
    label: "Playful: rounded shapes and price stickers",
  },
  minimal: {
    display: PUBLIC, body: PUBLIC, headingWeight: 300,
    grid: "flex flex-col divide-y divide-[color:var(--s-rule)]",
    imageFrame: "", imageAspect: "aspect-square", card: "", hero: "quiet",
    label: "Minimal: one typeface and a quiet product list",
  },
};

function luminance(hex: string): number {
  const v = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => {
    const c = parseInt(v.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

/** Text colour that stays readable on the accent: the store's own surface or ink. */
export function onAccent(brand: Brand): string {
  return contrast(brand.surface_color, brand.accent_color) >= contrast(brand.ink_color, brand.accent_color)
    ? brand.surface_color
    : brand.ink_color;
}

function mix(hex: string, withHex: string, amount: number): string {
  const p = (h: string) => [0, 2, 4].map((i) => parseInt(h.replace("#", "").slice(i, i + 2), 16));
  const [a, b] = [p(hex), p(withHex)];
  return "#" + a.map((v, i) => Math.round(v * (1 - amount) + b[i] * amount).toString(16).padStart(2, "0")).join("");
}

export function themeVars(brand: Brand): CSSProperties {
  const theme = THEMES[brand.visual_direction] ?? THEMES.editorial;
  return {
    "--s-accent": brand.accent_color,
    "--s-on-accent": onAccent(brand),
    "--s-ink": brand.ink_color,
    "--s-muted": mix(brand.ink_color, brand.surface_color, 0.38),
    "--s-surface": brand.surface_color,
    "--s-raised": mix(brand.surface_color, "#000000", 0.035),
    "--s-rule": mix(brand.ink_color, brand.surface_color, 0.82),
    "--s-display": theme.display,
    "--s-body": theme.body,
    "--s-heading-weight": String(theme.headingWeight),
  } as CSSProperties;
}
