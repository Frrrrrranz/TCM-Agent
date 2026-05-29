---
name: TCM-Agent Terminal
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
  on-surface-variant: '#bec9c2'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#88938d'
  outline-variant: '#3f4944'
  surface-tint: '#83d7b5'
  primary: '#83d7b5'
  on-primary: '#003828'
  primary-container: '#4ca081'
  on-primary-container: '#003122'
  inverse-primary: '#056c50'
  secondary: '#b4ccc2'
  on-secondary: '#20342e'
  secondary-container: '#384d46'
  on-secondary-container: '#a6beb4'
  tertiary: '#ffb3ae'
  on-tertiary: '#591b1a'
  tertiary-container: '#d07873'
  on-tertiary-container: '#501514'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#9ff4d0'
  primary-fixed-dim: '#83d7b5'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#d0e8de'
  secondary-fixed-dim: '#b4ccc2'
  on-secondary-fixed: '#0a1f19'
  on-secondary-fixed-variant: '#364b44'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3ae'
  on-tertiary-fixed: '#3d0608'
  on-tertiary-fixed-variant: '#76312f'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: jetbrainsMono
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: jetbrainsMono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 22px
  label-caps:
    fontFamily: jetbrainsMono
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.08em
  code-sm:
    fontFamily: jetbrainsMono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style

The design system is a high-utility, terminal-inspired interface tailored for Traditional Chinese Medicine (TCM) practitioners and researchers. It merges the clinical precision of a medical workstation with the efficiency of a modern command-line interface. 

The aesthetic is **Minimalist-CLI**: focused on readability, rapid information retrieval, and functional density. It evokes a sense of calm authority through a dark, low-distraction environment. Visual flourish is intentionally suppressed in favor of structural clarity, using monospace data blocks and structured dividers to organize complex diagnostic data. The emotional response should be one of "digital craftsmanship"—clean, reliable, and deeply technical.

## Colors

The palette is anchored in a high-contrast, dark-mode environment.
- **Backgrounds**: The core workspace uses `#0d0d0d`. Secondary panels and surfaces use a slightly lighter `#161616` to create depth without relying on shadows.
- **Accents**: A muted Jade Green (`#4a9e7f`) serves as the primary interactive signal, representing growth and vitality in a medicinal context.
- **Typography**: Primary content is rendered in a soft off-white (`#e8e6e3`) to reduce eye strain, while metadata and terminal "prompts" use a mid-tone grey.
- **System States**: Success markers use the Jade accent; warnings use a muted amber (`#c99a5e`); errors use a desaturated red (`#a34a4a`).

## Typography

This design system employs a dual-font strategy to distinguish between UI "chrome" and "content."
- **Inter**: Used for structural UI elements, navigation headers, and modal titles. It provides a modern, legible frame for the application.
- **JetBrains Mono**: The workhorse font for all AI outputs, diagnostic data, patient notes, and herb lists. The monospaced nature ensures that vertical alignment in lists and structured tables is preserved.

A generous **1.7 line height** is mandated for all body text to ensure that dense medical terminology and complex prescriptions remain readable during long research sessions.

## Layout & Spacing

The layout follows a **Fixed-Fluid hybrid** model. 
- **Sidebars**: Fixed at 280px for navigation and diagnostic history. They are collapsible to a 64px icon-only state.
- **Main Content**: A centered fluid container with a maximum width of 1024px to maintain line-length readability for monospace text.
- **Grid**: A 12-column grid is used for desktop layouts, while mobile collapses to a single column with a fixed 16px margin.
- **Rhythm**: All spacing is derived from a 4px base unit. Component padding is intentionally compact (8px-12px) to mimic the density of a terminal emulator, while vertical margins between message blocks are larger (24px) to separate distinct AI turns.

## Elevation & Depth

Depth is conveyed through **Tonal Layering** and **Borders** rather than shadows.
- **Level 0 (Base)**: `#0d0d0d` - The main application background.
- **Level 1 (Panels)**: `#161616` - Used for sidebars and top navigation bars.
- **Level 2 (Cards/Blocks)**: `#1c1c1c` - Used for chat bubbles or diagnostic cards.
- **Outlines**: A 1px solid border (`#2a2a2a`) is used to define boundaries between all major UI regions. 
- **Interactive Focus**: Active text inputs or focused cards receive a 1px border of the primary Jade color (`#4a9e7f`). No blurs or glass effects are permitted.

## Shapes

The design system utilizes a **Semi-Square** geometry. 
- **Standard Elements**: Buttons, inputs, and cards use a 4px (Soft) corner radius to provide a hint of modern refinement while maintaining a rigid, technical feel.
- **Pills**: Specific "Tool" widgets or status badges use a fully rounded (pill) shape to distinguish them as standalone interactive utilities within the square-heavy layout.
- **Separators**: 1px horizontal or vertical lines are used extensively to create logical groupings of data.

## Components

- **Buttons**: Flat, 4px corners. Primary buttons use the Jade background with black text. Secondary buttons use a jade outline with no fill.
- **Structured Message Blocks**: AI responses are contained in blocks with a subtle vertical Jade border on the left edge. Headers within these blocks use the "Label-Caps" typography style.
- **Tool Widgets**: Pill-shaped containers for specific functions (e.g., "Pulse Analysis" or "Tongue Map"). They use a secondary jade-tinted background (`#354a43`).
- **Lists**: Diagnostic lists use ASCII-style indicators (`-`, `+`, `>`) instead of standard bullet points.
- **Input Fields**: Terminal-style prompt inputs. No background fill; only a bottom border that turns Jade on focus. Includes a permanent `>` prefix.
- **Icons**: Icons are minimal and stroke-based. Where possible, use ASCII symbols (`✓`, `✗`, `⟳`, `⌬`) or the specific medicine glyph (`⚕`) to reinforce the TCM theme.