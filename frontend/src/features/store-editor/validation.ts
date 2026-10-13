// Client-side checks mirror the server's rules so people see problems as they type.
// The server re-validates everything; these are a convenience, not a guarantee.
import type { ProductInput } from "@/types/api";

const ZERO_DECIMAL = new Set(["JPY", "HUF", "TWD"]);

export function slugify(text: string): string {
  return text.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60).replace(/-+$/, "");
}

export function validateProduct(p: ProductInput, takenSlugs: string[]): Record<string, string> {
  const e: Record<string, string> = {};
  if (!p.name.trim()) e.name = "Add a product name.";
  if (!p.description.trim()) e.description = "Add a description.";
  const decimals = ZERO_DECIMAL.has(p.currency) ? 0 : 2;
  const pattern = decimals ? /^\d+(\.\d{1,2})?$/ : /^\d+$/;
  if (!pattern.test(p.price.trim())) {
    e.price = decimals ? "Use a number like 24 or 24.50." : `${p.currency} prices are whole numbers.`;
  } else if (Number(p.price) <= 0) {
    e.price = "Price must be more than zero.";
  } else if (Number(p.price) > 100000) {
    e.price = "Price can't be more than 100,000.";
  }
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(p.slug)) e.slug = "Use lowercase letters, numbers and hyphens.";
  else if (takenSlugs.includes(p.slug)) e.slug = "Another product already uses this URL name.";
  const url = p.image_url.trim();
  if (url && !(url.startsWith("https://") || (url.startsWith("/") && !url.startsWith("//")))) {
    e.image_url = "Use an https:// address or pick an image from the library.";
  }
  if (p.inventory != null && (!Number.isInteger(p.inventory) || p.inventory < 0)) {
    e.inventory = "Stock must be a whole number, 0 or more.";
  }
  return e;
}
