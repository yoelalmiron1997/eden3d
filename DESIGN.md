---
name: TecnoBear
description: Free in-browser generators for 3D printing, set on a dark industrial workbench faceplate.
colors:
  lima: "#c5f05b"
  lima-hover: "#d6f784"
  lima-ink: "#0b1204"
  logo-yellow: "#e9eb9f"
  floor: "#090e0f"
  plate: "#101719"
  plate-sunken: "#0c1213"
  rule: "#344346"
  rule-faint: "#1d2729"
  text: "#f6f8f6"
  text-muted: "#a3b1ae"
  grid-line: "rgba(197, 240, 91, 0.045)"
  error: "#ff9b85"
  floor-light: "#eef1ec"
  plate-light: "#ffffff"
  plate-sunken-light: "#f5f7f3"
  rule-light: "#b5c1be"
  rule-faint-light: "#d7dfdc"
  text-light: "#0d1314"
  text-muted-light: "#46524f"
  acento-light: "#3d5f00"
  grid-line-light: "rgba(13, 19, 20, 0.05)"
  error-light: "#8a2614"
typography:
  display:
    fontFamily: "Barlow Condensed, Inter, sans-serif"
    fontSize: "clamp(3.4rem, 7.4vw, 6rem)"
    fontWeight: 700
    lineHeight: 0.88
    letterSpacing: "-0.005em"
  headline:
    fontFamily: "Barlow Condensed, Inter, sans-serif"
    fontSize: "clamp(2.4rem, 4.6vw, 3.75rem)"
    fontWeight: 700
    lineHeight: 0.92
    letterSpacing: "0.01em"
  title:
    fontFamily: "Barlow Condensed, Inter, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: "0.01em"
  title-sm:
    fontFamily: "Barlow Condensed, Inter, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "0.02em"
  wordmark:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.02em"
  engraving:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.3em"
  body:
    fontFamily: "Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "\"cv11\", \"ss01\""
  body-sm:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14.5px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Inter, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.1em"
  caption:
    fontFamily: "Inter, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.1em"
rounded:
  none: "0px"
  control: "2px"
  isotipo: "50%"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "28px"
  2xl: "40px"
  grid-cell: "48px"
  gutter: "clamp(16px, 4vw, 48px)"
  section: "clamp(64px, 7vw, 96px)"
  container: "1360px"
  nav-height: "64px"
  bevel: "16px"
  bevel-button: "12px"
  bevel-card: "18px"
  bevel-plate: "28px"
components:
  button-primary:
    backgroundColor: "{colors.lima}"
    textColor: "{colors.lima-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 22px"
    height: "50px"
  button-primary-hover:
    backgroundColor: "{colors.lima-hover}"
    textColor: "{colors.lima-ink}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 22px"
    height: "50px"
  button-secondary-hover:
    textColor: "{colors.lima}"
  filter-chip:
    backgroundColor: "transparent"
    textColor: "{colors.text-muted}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "44px"
  filter-chip-active:
    backgroundColor: "{colors.lima}"
    textColor: "{colors.lima-ink}"
  search-input:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0 14px 0 44px"
    height: "48px"
  nav-bar:
    backgroundColor: "{colors.floor}"
    textColor: "{colors.text-muted}"
    height: "{spacing.nav-height}"
  nav-link:
    textColor: "{colors.text-muted}"
    padding: "10px 12px"
  nav-link-active:
    textColor: "{colors.text}"
  tool-card:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.text}"
    rounded: "{rounded.none}"
    padding: "18px 20px 20px"
  hero-plate:
    backgroundColor: "{colors.plate}"
    rounded: "{rounded.none}"
    width: "560px"
  modal:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
---

# Design System: TecnoBear

## Overview

**Creative North Star: "The Workbench Faceplate"**

TecnoBear's interface is the faceplate of a digital-fabrication bench. The page is a dark machined floor ruled with a near-invisible 1px technical grid; content sits on flat plates bounded by 1px rules, each plate with a single 45° bevel cut into one corner. The tools read as machine cards, the hero object is a graduated turntable dial with the original TecnoBear isotipo floating gently at its center (it never spins), and the brand motto is engraved around the ring. Nothing floats, glows or rounds into a pill; structure comes from rules, tonal plates and condensed stamped capitals.

The system is dark by default and supports a light variant (`html[data-theme="light"]`) because the site-wide theme toggle must keep working; both variants share every rule below and differ only in the neutral and accent-stroke tokens. Density is calm: one 1360px container, generous section breaks, and grids of four that collapse to two and then one.

Scope: the whole site. The home page carries the full composition (`web/index.html`, `web/home.css`, `web/home.js`, catalog data in `web/herramientas.js`); the tool pages (macetas, mate, sopa, topper, admin, calidad) get the same tokens, header, controls and plates from the industrial layer at the end of the shared `web/style.css`. The older green-on-cream rules earlier in that file are overridden and are not an authority for new work.

**Key Characteristics:**
- Dark machined floor (dark default) with a 48px technical grid of 1px lime-tinted lines at 4.5% opacity (32px cells under 640px).
- Flat plates, 1px rules, one 45° bevel per plate with the diagonal rule drawn on the cut.
- Lime as the single action/active color and the color of instrument markings; the logo's pale yellow reserved for the brand.
- Barlow Condensed uppercase for every heading; Inter for everything else.
- Square corners: 2px on controls, 0 on plates; no pills.
- One quiet moving signature: the hero isotipo floats a few millimetres up and down; it never rotates, and the navbar and footer logos are still.

## Colors

A near-black teal-graphite neutral ramp carrying one acid lime accent and one brand-reserved pale yellow.

### Primary
- **Lathe Lime** (lima): the filled call to action, the pressed filter chip, the active nav underline, the focus outline, text selection, and the instrument markings (dial major ticks, crosshair, plate corner brackets, benefit icons, the accent word "en 3D" in the hero title). Its fill stays the same in both themes.
- **Lime Hot** (lima-hover): hover fill of lime buttons only.
- **Lime Ink** (lima-ink): text and icons on any lime fill.
- **Deep Lime Stroke** (acento-light): in the light theme, lime used as text or stroke (hover text, outlines, ticks, icons) switches to this dark olive so it reads on pale plates.

### Secondary
- **Isotipo Yellow** (logo-yellow): the logo's own pale yellow. Used for the engraved motto ("Despertá tu tecnología") under the hero plate and in the footer, and for the Pro role badge. In the light theme the motto falls back to body text color.

### Neutral
- **Machined Floor** (floor / floor-light): page background beneath the grid; also the translucent nav bar (94% mix with transparency).
- **Plate** (plate / plate-light): every raised plate: tool cards, hero plate, search field, modals, the ring that seats the isotipo.
- **Sunken Plate** (plate-sunken / plate-sunken-light): photo wells inside cards, the footer band, modal inputs.
- **Rule** (rule / rule-light): primary 1px borders of plates, buttons, chips and inputs; section top rules; dial rings.
- **Faint Rule** (rule-faint / rule-faint-light): internal dividers: card borders at rest, index row separators, benefit cell dividers, nav bottom edge.
- **Bright Text** (text / text-light): headings and primary text.
- **Graphite Text** (text-muted / text-muted-light): lead paragraph, descriptions, category labels, inactive nav and chips, placeholders (all AA on their plates).
- **Grid Line** (grid-line / grid-line-light): only for the background technical grid.
- **Warning Coral** (error / error-light): login and form error messages.

### Named Rules
**The Two-Lime Rule.** Lime has two jobs and two tokens: `lima` is a fill (always #c5f05b, always with `lima-ink` on it); the accent used as text or stroke follows the theme (`lima` in dark, `acento-light` in light). Never put lime text on a light plate.

**The Instrument-Marking Rule.** Lime appears only on actions, active/pressed/focused states, and small instrument markings. It never fills a section, a card or a large surface.

**The Brand-Yellow Rule.** Isotipo Yellow belongs to the brand (motto, Pro badge, the logo itself). It never signals UI state.

## Typography

**Display Font:** Barlow Condensed 600/700 (self-hosted, fallback Inter, sans-serif)
**Body Font:** Inter variable (self-hosted, fallback system-ui, -apple-system, Segoe UI, sans-serif), with `cv11` and `ss01` enabled
**Label Font:** Inter 600, tracked uppercase

**Character:** Condensed capitals stamped like plate lettering over a neutral, precise grotesque. The contrast in width and case does the hierarchy work, so weights stay few.

### Hierarchy
- **Display** (Barlow Condensed 700, clamp(3.4rem, 7.4vw, 6rem), line-height 0.88, uppercase, max 11ch): the hero title only; one accent word may take the lime stroke color. Under 640px it scales to clamp(3rem, 15.5vw, 4.4rem).
- **Headline** (Barlow Condensed 700, clamp(2.4rem, 4.6vw, 3.75rem), 0.92, uppercase): section titles ("Herramientas disponibles", "Hechas para imprimir").
- **Title** (Barlow Condensed 700, 1.75rem, 0.95, uppercase): tool card names; benefit titles at 1.6rem; modal titles at 2rem.
- **Title Small** (Barlow Condensed 600, 20px, 1.1, uppercase): rows of the hero tool index.
- **Wordmark** (Barlow Condensed 700, 24px; 21px under 640px): the "TecnoBear" text beside the isotipo. Set as text, never rotated.
- **Engraving** (Barlow Condensed 600, 15px, letter-spacing 0.28–0.32em, uppercase): the motto on and under the dial and in the footer.
- **Body** (Inter 400, 16px, 1.55): running text; the hero lead runs at clamp(1rem, 1.25vw, 1.125rem), max 54ch.
- **Body Small** (Inter 400, 14.5px): card descriptions, benefit copy (max 34ch), footer links.
- **Label** (Inter 600, 13px, 0.06–0.1em, uppercase): buttons, filter chips, account buttons.
- **Caption** (Inter 600, 11–12px, 0.1–0.14em, uppercase): category lines, the "Ver detalles" photo tag, the modal tool tag, results counter text (14px, 0.08em).

### Named Rules
**The Stamped Title Rule.** Every h1–h3 is Barlow Condensed uppercase with balanced wrapping; nothing else uses Barlow Condensed except the wordmark, index rows, the results count numeral and the engraving.

**The Engraving Rule.** Wide tracking (0.28em and up) is reserved for the brand motto. Labels track at 0.06–0.14em, never wider.

## Layout

One centered container of 1360px with a fluid gutter of clamp(16px, 4vw, 48px). The background grid is 48px (32px under 640px), and spacing steps sit on an 8px-derived rhythm (8, 12, 16, 20, 28, 40). Sections are separated by clamp(64px, 7vw, 96px) of top padding; the footer opens with clamp(72px, 10vw, 128px).

The nav is sticky at 64px (60px under 640px). The hero is a two-column grid (1.08fr / 0.92fr, gap clamp(32px, 5vw, 80px)): title, lead, the two CTAs and a ruled index of the tools on the left; the square hero plate (max 560px) with the motto rule beneath it on the right. Catalog and benefits use four equal columns (20px gap for cards; benefits as a single ruled strip with 1px dividers between cells).

Responsive: at 1180px cards and benefits go to two columns, filters become a 4-up grid, the search bar stacks; at 1080px the nav collapses to a hamburger panel and the hero stacks with the plate first (max 420px) and the motto rule hidden; at 640px everything is one column, the plate drops to 220px and CTAs go full width; at 380px the wordmark hides and only the isotipo remains. No horizontal scroll at 390px.

## Elevation & Depth

Depth is ruled, not raised. Plates sit flat on the floor and are distinguished by tone (plate vs floor vs sunken plate) and by 1px rules; hover states change border and stroke color, not height. Shadows exist in only three places: the hero plate's ambient drop, open modals, and the mobile menu panel.

### Shadow Vocabulary
- **Plate drop** (`box-shadow: 0 18px 40px -18px rgba(0, 0, 0, .7)`; light: `0 18px 40px -22px rgba(13, 19, 20, .35)`): the hero plate only.
- **Isotipo seat** (`box-shadow: 0 0 0 10px <plate>, 0 0 0 11px <rule>`): a plate-colored collar with a 1px rule that seats the floating isotipo in the dial (6px/7px under 640px).
- **Modal drop** (`box-shadow: 0 24px 48px -16px rgba(0, 0, 0, .7)`): dialogs, over a flat rgba(5, 8, 9, .78) backdrop with no blur.
- **Menu drop** (`box-shadow: 0 24px 40px -20px rgba(0, 0, 0, .7)`): the collapsed-nav panel.

### Named Rules
**The Ruled-Not-Raised Rule.** Cards and controls never gain a shadow or lift on hover; they answer with a brighter rule, a lime bevel line, or a lime stroke. A 1px press (`translateY(1px)`) on buttons is the only movement.

## Shapes

Corners are square: 2px on interactive controls (buttons, chips, inputs, nav pills, modals), 0 on plates. Each plate carries one 45° bevel made with `clip-path`, and a 1px rule is drawn along the diagonal so the cut reads as machined: tool cards cut top-right (18px), the hero plate cuts top-right and bottom-left (28px; 16px under 640px), the lime CTA cuts bottom-right (12px). The hero plate also carries two 22px lime corner brackets (top-left, bottom-right). The only circle in the system is the isotipo and the dial around it; the empty-results state uses a 1px dashed rule.

### Named Rules
**The One Bevel Rule.** One cut corner per object (the hero plate's diagonal pair is the single exception), always 45°, always with its diagonal rule. No pills, no rounded cards, no radius above 2px except the isotipo.

## Components

### Buttons
Tactile and blunt, like labelled switches on a panel.
- **Shape:** 2px corners, 50px tall (48px in cards), 22px side padding, Label type uppercase, icon 18px with a 3px slide on hover.
- **Primary (lime):** lime fill, lime-ink text, bottom-right 12px bevel; hover goes to Lime Hot. One per view region ("Explorar herramientas").
- **Secondary (outline):** transparent with a 1px Rule border and bright text; hover turns border and text to the accent stroke. Used for "Ver tutoriales", "Abrir herramienta" (full width, label left, arrow right) and "Ver todas".
- **Focus:** 2px lime outline, 3px offset, on every focusable element.

### Chips (category filters)
- **Style:** 44px tall, 1px Rule border, transparent, Graphite Text, Label type with an 18px line icon.
- **State:** hover brightens text and border to muted; pressed (`aria-pressed="true"`) is a solid lime fill with lime-ink text. Exactly one is pressed.

### Cards / Containers (tool cards)
- **Corner Style:** square with an 18px top-right bevel; the bevel's diagonal rule turns lime on hover and focus-within.
- **Background:** Plate; photo well in Sunken Plate, square (16:11 between 640 and 1180px), separated by a faint rule.
- **Shadow Strategy:** none (see Ruled-Not-Raised).
- **Border:** 1px Faint Rule at rest, Rule on hover.
- **Internal Padding:** 18px 20px 20px; order is title, description, category line (ruled on top), then the full-width outline button.
- **Photo behavior:** the photo is a button opening the tool's modal; image scales 1.04 on card hover; a dark "Ver detalles" tag slides in bottom-left (always visible on touch).

### Inputs / Fields
- **Style:** 48px, Plate background, 1px Rule border, 2px corners, 20px magnifier icon inset 14px, lime caret.
- **Focus:** border and a 1px ring in the accent stroke color (no glow).

### Navigation
- **Style:** sticky 64px bar, floor color at 94% opacity, faint bottom rule. Isotipo (40px; 34px under 640px) plus wordmark at left; Inter 500 14px links in Graphite Text, bright on hover; the current link gets a 2px lime underline. YouTube link is a ruled 2px-corner button; theme and account controls follow the same outline language (account sign-in has a lime border that fills on hover).
- **Mobile (≤1080px):** 44px ruled hamburger toggles a full-width panel below the bar with 52px rows separated by faint rules and the active marker shortened to a 24px lime stub.

### Hero Plate and Dial (signature)
A square Plate with the two-corner bevel, lime corner brackets and the plate drop. Inside, an SVG graduated dial: outer and inner 1px Rule rings, minor ticks in Rule, major ticks every 30° in the accent stroke, a dotted inner ring, a lime crosshair at the four cardinal points, and the motto engraved along a circular path in Graphite Text. The original isotipo (52% of the plate) floats in the center in its plate-colored seat. Beneath the plate, at desktop widths, the motto repeats in Isotipo Yellow after a 1px rule.

### Tool Index (signature)
A ruled ordered list under the hero CTAs: each row is a link with the short tool name (Title Small), its category (Caption, muted) and an arrow icon; rows are separated by faint rules under a top Rule. Hover indents the row 10px and turns it and its arrow to the accent stroke.

### Benefit Strip
Four cells inside one ruled band (top and bottom Rule, faint dividers between cells), each with a 30px lime line icon, a Title and Body Small copy. No card chrome.

### Motion
The logo never rotates. Only the hero isotipo moves: it floats between +5px and -7px on the Y axis over 3.6s, eased in and out (`cubic-bezier(.45, 0, .55, 1)`), alternating forever. The navbar and footer logos are still. Cards and benefit cells below the fold enter once with an 18px rise over 0.7–0.9s on `cubic-bezier(.16, 1, .3, 1)`, staggered 70ms in groups of four; content is visible without JavaScript. `prefers-reduced-motion` stops the float, the entrance and all transitions.

## Do's and Don'ts

### Do:
- **Do** build every new surface on the dark floor with the 48px grid, flat Plate containers and 1px Rule borders, and wire the light variant through the same tokens under `html[data-theme="light"]`.
- **Do** cut exactly one 45° bevel per plate with `clip-path` and draw its 1px diagonal rule.
- **Do** keep lime to actions, active/pressed/focus states and small instrument markings; use `lima-ink` on lime fills and the theme's accent stroke for lime text.
- **Do** set every heading in Barlow Condensed uppercase and everything else in Inter, both self-hosted.
- **Do** use the vector logo `web/assets/marca/logo-tecnobear.svg` (a trace of the original `logo-tecnobear-original.png`, 99.4% pixel match) untouched; only the hero isotipo moves, with a gentle float.
- **Do** use 1.6px square-capped, miter-joined line icons from the inline sprite, 16–20px (30px in the benefit strip).
- **Do** keep text AA on its plate in both themes and show the 2px lime focus outline on every control.

### Don't:
- **Don't** use pills, rounded cards or any radius above 2px; the only circles are the isotipo and its dial.
- **Don't** lift cards with shadows or translate them on hover; answer hover with a brighter rule or lime stroke.
- **Don't** add outer glows, neon halos or backdrop blur.
- **Don't** fill large areas with lime, or use Isotipo Yellow for UI state.
- **Don't** redraw, recolor, rotate or spin the logo, or replace it with an emoji or icon.
- **Don't** treat the older green-on-cream rules at the top of `web/style.css` as a reference for new work; the industrial layer at its end is the authority.

## Additions

**Theme selector.** Every page header carries a two-option segmented control (`.tema-sel`, from `web/theme.js`): Oscuro (the brand default, also when nothing was chosen) and Claro. 1px Rule frame, 3px inset; the pressed option is a Bright Text fill with Floor text. Under 640px the labels collapse to icons (still named for assistive tech).

**Plans (Gratis / Premium).** Two equal plates under the benefits strip, each with the 22px bevel. Gratis lists what the free plan includes and, in muted text with a cross, that pieces carry the watermark; its outline action creates a free account (or goes to the tools when accounts are off). Premium has the accent-stroke border and bevel rule, a faint 6% lime wash at the top, an Isotipo Yellow "Comunidad" tag, and the lime primary action "Quiero Premium", which goes to the real Instagram account. No prices are shown because none exist.

**Tool pages.** Same header as the home (original logo, wordmark, tool name after a 1px rule, Inicio / Herramientas, theme selector, account). Configuration panels are Plates with a 16px bevel, legends are Barlow Condensed uppercase, controls are 2px-cornered on Sunken Plate, the primary action is the lime clipped button, pressed segments/chips/tabs are lime with Lime Ink, and the 3D stage sits on a dark radial floor.
