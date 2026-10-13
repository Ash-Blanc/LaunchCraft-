"""Deterministic sample catalogues used by the demo assistant.

These are hand-written samples, not model output. Product art lives in
frontend/public/demo and is original illustration made for this project.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SampleProduct:
    slug: str
    name: str
    description: str
    price: str  # USD-equivalent sample price
    image_alt: str

    @property
    def image_url(self) -> str:
        return f"/demo/{self.slug}.svg"


@dataclass(frozen=True)
class SampleCatalog:
    key: str
    label: str
    keywords: tuple[str, ...]
    direction: str
    accent: str
    ink: str
    surface: str
    tagline: str
    products: tuple[SampleProduct, ...]
    spares: tuple[SampleProduct, ...] = field(default=())


STATIONERY = SampleCatalog(
    key="stationery", label="botanical stationery",
    keywords=("paper", "card", "stationery", "print", "journal", "notebook", "letter",
              "envelope", "botanical", "pressed", "wedding", "gift wrap", "planner"),
    direction="botanical", accent="#3F6212", ink="#1F2A1C", surface="#F5F2EA",
    tagline="Paper goods pressed and bound by hand",
    products=(
        SampleProduct("pressed-fern-cards", "Pressed Fern Card Set",
                      "Six folded cards, each holding a real fern frond pressed under glassine. "
                      "Blank inside, A6, with recycled kraft envelopes.",
                      "18.00", "Six cream cards each holding a pressed green fern"),
        SampleProduct("seed-paper-tags", "Wildflower Seed Paper Tags",
                      "Twelve gift tags made from paper embedded with wildflower seeds. Soak and "
                      "plant them after unwrapping; most sprout within two weeks.",
                      "9.50", "Speckled paper gift tags tied with natural twine"),
        SampleProduct("linen-envelopes", "Oat Linen Envelopes",
                      "Twenty textured envelopes in a warm oat shade with a linen finish, sized "
                      "for A6 cards and gummed for easy sealing.",
                      "7.00", "A fanned stack of oat-coloured linen envelopes"),
        SampleProduct("field-notebook", "Hand-Bound Field Notebook",
                      "A pocket notebook with 64 pages of dot-grid cotton paper, sewn with waxed "
                      "thread into a stiff botanical-print cover.",
                      "24.00", "A small notebook with a leaf-print cover and visible stitching"),
    ),
    spares=(
        SampleProduct("herbarium-labels", "Herbarium Label Pad",
                      "Fifty tear-off labels printed in the style of old herbarium sheets, with "
                      "lines for name, place and date collected.",
                      "12.00", "A pad of printed herbarium labels with a pencil"),
        SampleProduct("botanical-wrap", "Botanical Wrapping Paper",
                      "Three folded sheets of heavyweight wrapping paper printed with fern and "
                      "yarrow line drawings, 50 by 70 centimetres each.",
                      "14.00", "Folded wrapping paper printed with fern line drawings"),
    ),
)

CERAMICS = SampleCatalog(
    key="ceramics", label="studio ceramics",
    keywords=("ceramic", "pottery", "potter", "mug", "clay", "kiln", "stoneware", "bowl",
              "kitchen", "coffee", "vase", "tableware", "glaze"),
    direction="workshop", accent="#1F5F5B", ink="#22201C", surface="#F3F0EA",
    tagline="Everyday stoneware, thrown in small batches",
    products=(
        SampleProduct("speckled-mug", "Speckled Oat Mug",
                      "A 350 ml wheel-thrown stoneware mug with an oat glaze that breaks to "
                      "brown at the rim. Dishwasher and microwave safe.",
                      "32.00", "A speckled cream mug with a darker rim"),
        SampleProduct("nesting-bowls", "Nesting Prep Bowls, Set of 3",
                      "Three stoneware bowls that stack inside each other, glazed inside and "
                      "left raw outside for grip. 8, 11 and 14 cm across.",
                      "58.00", "Three stacked stoneware bowls in graduated sizes"),
        SampleProduct("pour-over-cone", "Pour-Over Coffee Cone",
                      "A single-cup coffee dripper with spiral ribs inside for even flow. Fits "
                      "standard number 2 paper filters and most mugs.",
                      "44.00", "A ribbed ceramic coffee dripper resting on a mug"),
        SampleProduct("bud-vase", "Ash-Glaze Bud Vase",
                      "A 12 cm vase for a single stem, finished in a runny ash glaze, so no two "
                      "are quite the same. Watertight.",
                      "28.00", "A small round vase holding a single dried stem"),
    ),
    spares=(
        SampleProduct("serving-plate", "Wide Rim Serving Plate",
                      "A 30 cm serving plate with a broad flat rim, glazed in matte white with "
                      "an exposed clay foot.",
                      "66.00", "A wide white plate with a broad rim"),
        SampleProduct("spoon-rest", "Stoneware Spoon Rest",
                      "A small oval rest for the stove side, with a shallow well that keeps "
                      "drips off the counter.",
                      "16.00", "An oval ceramic spoon rest holding a wooden spoon"),
    ),
)

APOTHECARY = SampleCatalog(
    key="apothecary", label="home apothecary",
    keywords=("candle", "soap", "scent", "fragrance", "skincare", "skin", "bath", "balm",
              "oil", "apothecary", "wellness", "aroma", "self-care", "beauty"),
    direction="editorial", accent="#6B2C5C", ink="#231C22", surface="#F6F2EE",
    tagline="Small-batch scents for slow evenings",
    products=(
        SampleProduct("night-candle", "Night Garden Candle",
                      "A soy and coconut wax candle scented with jasmine, vetiver and a little "
                      "smoke, poured into reusable amber glass. Around 45 hours.",
                      "36.00", "An amber glass candle with a cotton wick"),
        SampleProduct("hand-balm", "Calendula Hand Balm",
                      "A rich balm of shea butter and calendula-infused oil for dry hands, in a "
                      "60 ml aluminium tin. Unscented.",
                      "19.00", "A round metal tin of hand balm, lid off"),
        SampleProduct("bath-oil", "Fig Leaf Bath Oil",
                      "A light blend of almond and jojoba oils scented with green fig leaf. Add "
                      "a capful to warm water. 100 ml glass bottle.",
                      "27.00", "A slim glass bottle of pale green bath oil"),
        SampleProduct("cedar-matches", "Cedar Safety Matches",
                      "Fifty long cedar matches in a printed box with a striking strip on both "
                      "sides. Long enough to reach a deep wick.",
                      "8.00", "A printed matchbox with long matches fanned beside it"),
    ),
    spares=(
        SampleProduct("room-mist", "Linen Room Mist",
                      "A water-based mist of lavender and clean linen for pillows and curtains. "
                      "100 ml bottle with a fine sprayer.",
                      "22.00", "A frosted spray bottle beside folded linen"),
        SampleProduct("travel-candle", "Travel Candle Tin",
                      "The Night Garden scent in a lidded 100 g tin for travel and small rooms. "
                      "Around 20 hours.",
                      "18.00", "A small lidded candle tin"),
    ),
)

CATALOGS: tuple[SampleCatalog, ...] = (STATIONERY, CERAMICS, APOTHECARY)
CATALOGS_BY_KEY = {c.key: c for c in CATALOGS}

PLACEHOLDER_IMAGE = "/demo/parcel.svg"
PLACEHOLDER_ALT = "Placeholder illustration of a wrapped parcel"


def match_catalog(text: str) -> tuple[SampleCatalog, int]:
    """Pick the sample catalogue whose keywords appear most often. Ties keep list order."""
    lowered = text.lower()
    best, best_score = STATIONERY, 0
    for catalog in CATALOGS:
        score = sum(1 for k in catalog.keywords if k in lowered)
        if score > best_score:
            best, best_score = catalog, score
    return best, best_score
