# Design notes

## Direction

Paper surfaces, blue-black ink, and one accent: a rubber-stamp blue. The product's pitch is that it only calls a store ready when the evidence says so. The visual language borrows from dockets, receipts and stamps to make that tangible.

## Tokens (`frontend/src/app/globals.css`)

| Token | Value | Use |
|---|---|---|
| paper | `#F7F4EE` | app background |
| panel | `#EFEAE0` | side panes, preview backdrop |
| sheet | `#FFFDF9` | forms, cards, inputs |
| rule / rule-strong | `#DCD4C5` / `#C4BAA7` | dividers, input borders |
| ink / ink-2 / ink-3 | `#1B1E26` / `#555B66` / `#7A7F88` | text, secondary text, placeholders |
| stamp | `#2A45C2` | the one accent: primary CTA, selection, focus ring, assistant markers |
| pass / fail / wait | `#2E6B3A` / `#A42A1F` / `#8C6512` | check results only, never decoration |

**Type.**
- Newsreader (optical sizes) is for headings, set in sentence case.
- Public Sans is for the interface, with tabular figures for prices.
- Storefronts add Young Serif and Bricolage Grotesque. Every font is self-hosted from npm, with no third-party font requests.

**Radii vary by hierarchy.** Inputs and buttons use 4px, sheets 8px, and the phone preview 18px.

## The one bold element

The launch docket has perforated edges, dashed rules, and a rotated double-border stamp reading READY TO LAUNCH or NOT READY. It's the only animated element on a page: the stamp lands once when a report arrives. Reduced motion disables it.

## Deliberately avoided

- Gradients and glassmorphism.
- Uppercase eyebrow labels.
- Rows of identical feature cards.
- Invented metrics or testimonials.
- Emoji.

Numbered markers appear only on the onboarding steps, because those really are a sequence.

## Storefront looks

Each look is a different layout, not a palette swap. All of them use container queries so the preview's phone width behaves like a real phone.

| Look | Type | Hero | Grid |
|---|---|---|---|
| Editorial | Newsreader | split masthead with lead product | 3-col magazine grid |
| Botanical | Young Serif | centred, arched image | 2-col, arched images |
| Workshop | Bricolage, heavy | full-bleed accent block | dense ruled 4-col catalogue |
| Playful | Bricolage | rounded accent card with price sticker | rounded tiles, price stickers |
| Minimal | Public Sans light | quiet title | single-column list with inline Add |

## Accessibility baseline

- Visible 2px focus ring everywhere.
- Native `<dialog>` for confirmations.
- Labelled form fields with errors tied by `aria-describedby`.
- Status messages in live regions.
- Checks state their result in text, not colour alone.
- Text on accent colours is chosen by contrast ratio, and the brand editor warns when text contrast falls below 4.5:1.
