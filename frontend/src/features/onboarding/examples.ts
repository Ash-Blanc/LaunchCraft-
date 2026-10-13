import type { BusinessBrief } from "@/types/api";

export const EMPTY_BRIEF: BusinessBrief = {
  business_name: "",
  niche: "",
  audience: "",
  personality: "",
  visual_direction: "auto",
  example_products: "",
  price_min: "",
  price_max: "",
  currency: "USD",
  market: "",
};

export const EXAMPLE_BRIEFS: BusinessBrief[] = [
  {
    business_name: "Slow Kiln",
    niche: "Handmade stoneware mugs, bowls and coffee gear",
    audience: "Home cooks and coffee people who buy fewer, better things",
    personality: "Sturdy everyday pottery, thrown in small batches",
    visual_direction: "auto",
    example_products: "",
    price_min: "15",
    price_max: "70",
    currency: "USD",
    market: "United States",
  },
  {
    business_name: "Night Garden Apothecary",
    niche: "Small-batch candles, bath oils and hand balm",
    audience: "People who like a slow evening routine and give thoughtful gifts",
    personality: "Small-batch scents for slow evenings",
    visual_direction: "auto",
    example_products: "",
    price_min: "",
    price_max: "",
    currency: "GBP",
    market: "United Kingdom",
  },
  {
    business_name: "Fern & Fold",
    niche: "Botanical stationery and pressed-flower cards",
    audience: "Gift buyers and letter writers",
    personality: "Paper goods pressed and bound by hand",
    visual_direction: "botanical",
    example_products: "Pressed fern card set - 18\nWildflower seed tags - 9.50\nWax seal kit - 26",
    price_min: "5",
    price_max: "40",
    currency: "EUR",
    market: "Germany and the Netherlands",
  },
];

const BRIEF_KEY = "launchcraft:brief";

export function saveBrief(brief: BusinessBrief) {
  try {
    window.sessionStorage.setItem(BRIEF_KEY, JSON.stringify(brief));
  } catch {
    /* not essential */
  }
}

export function loadSavedBrief(): BusinessBrief | null {
  try {
    const raw = window.sessionStorage.getItem(BRIEF_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<BusinessBrief>;
    return { ...EMPTY_BRIEF, ...parsed };
  } catch {
    return null;
  }
}
