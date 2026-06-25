---
name: DineAI
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#d8c3ad'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#a08e7a'
  outline-variant: '#534434'
  surface-tint: '#ffb95f'
  primary: '#ffc174'
  on-primary: '#472a00'
  primary-container: '#f59e0b'
  on-primary-container: '#613b00'
  inverse-primary: '#855300'
  secondary: '#4fdbc8'
  on-secondary: '#003731'
  secondary-container: '#04b4a2'
  on-secondary-container: '#003f38'
  tertiary: '#ffbda8'
  on-tertiary: '#5d1900'
  tertiary-container: '#ff9571'
  on-tertiary-container: '#7e2500'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffddb8'
  primary-fixed-dim: '#ffb95f'
  on-primary-fixed: '#2a1700'
  on-primary-fixed-variant: '#653e00'
  secondary-fixed: '#71f8e4'
  secondary-fixed-dim: '#4fdbc8'
  on-secondary-fixed: '#00201c'
  on-secondary-fixed-variant: '#005048'
  tertiary-fixed: '#ffdbd0'
  tertiary-fixed-dim: '#ffb59d'
  on-tertiary-fixed: '#390c00'
  on-tertiary-fixed-variant: '#832600'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-ai:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.1em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  2xl: 64px
  gutter: 20px
  margin-mobile: 16px
  margin-desktop: 40px
---

## Brand & Style
The design system is engineered for a premium, AI-driven gastronomic experience. The brand personality is sophisticated, predictive, and "concierge-like," blending high-end culinary aesthetics with cutting-edge technology. 

The visual style is **Modern Glassmorphism** with a **Linear-inspired** technical edge. It utilizes deep, atmospheric layering, subtle translucency, and precision-engineered accents to evoke a sense of exclusivity and intelligence. The interface should feel like a dark, high-end restaurant interior—focused, moody, and illuminated by intentional "light leaks" and glowing interactive states. High-contrast typography and generous whitespace ensure that while the environment is dark, the content remains the hero.

## Colors
The palette is rooted in a "Deep Charcoal" base to provide maximum contrast for imagery and accent glows. 

- **Primary (Amber):** Used for primary actions, ratings, and highlighting the "perfect match."
- **Secondary (Teal):** Used for functional success states, health-conscious tags, or AI "thinking" indicators.
- **Tertiary (Deep Orange):** Used for urgency, limited-time offers, or spicy/vibrant flavor profiles.
- **Surface:** A navy-tinged dark blue creates depth against the pure black background, forming the basis for glassmorphic cards.
- **Interactive States:** Use a 10% opacity white overlay for hovers and the primary accent for focus glows.

## Typography
Typography follows a strict hierarchy. **Outfit** is reserved for headlines to provide a modern, geometric character with high tracking in uppercase labels. **Inter** handles all functional and body text for maximum legibility.

A specific **AI Content** style is defined: it uses an italicized posture or a subtle weight shift to distinguish machine-generated recommendations from static data. For mobile, display sizes scale down aggressively to maintain a single-column focus without excessive wrapping.

## Layout & Spacing
The layout uses a **Fluid Grid** system with a focus on centered content blocks. 
- **Mobile:** 4-column grid, 16px margins, 16px gutters.
- **Desktop:** 12-column grid, max-width 1200px, 40px margins.

Spacing follows a 4px baseline. Use `xl` (40px) for section vertical spacing and `md` (16px) for internal card padding. Navigation elements and chips should maintain a "breathable" feel, avoiding density in favor of a premium, relaxed browsing experience.

## Elevation & Depth
Depth is created through **Tonal Layers** and **Glassmorphism** rather than traditional heavy shadows.
- **Level 0 (Background):** #0F0F0F.
- **Level 1 (Cards):** #1A1A2E with a 0.6 opacity and 20px backdrop blur. Borders are 1px solid, 0.1 opacity white.
- **Level 2 (Modals/Popovers):** Higher opacity (#1A1A2E at 0.9) with a subtle "Ambient Glow" shadow using the Primary Accent color at 5% opacity.

Interactive elements use "Linear" glows: a 1px inner border highlight on the top edge to simulate a light source from above.

## Shapes
The shape language is consistently **Rounded**. 
- **Standard Cards/Inputs:** 0.5rem (8px).
- **Pill Toggles/Buttons/Chips:** 100px (fully rounded).
- **Large Containers:** 1rem (16px).

This balance of architectural squares and organic pills reflects the precision of AI and the approachability of a dining assistant.

## Components
- **Buttons:** Primary buttons are solid Amber (#F59E0B) with dark text. Secondary buttons use the "Ghost" style: transparent background with the 1px glass border.
- **Pill Toggles:** Fully rounded tracks with a sliding physical-style knob. Active state should trigger a subtle Amber outer glow.
- **Cards:** Incorporate "Staggered Entrances"—when a list loads, cards should fade in and slide up 10px sequentially.
- **Star Ratings:** Custom-drawn, sharp-edged stars. Filled stars use Primary Amber; empty stars use the Surface border color.
- **Chips:** Small, pill-shaped tags for cuisine types. Background: rgba(255, 255, 255, 0.05).
- **Skeleton Loaders:** Use a shimmering gradient from #1A1A2E to #252545 to maintain the glassmorphic depth while data fetches.
- **AI Recommendation Engine:** A special container with a gradient border (Amber to Teal) and a pulsing background blur to signify "active processing."