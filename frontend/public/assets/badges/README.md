# Plan verified badge assets

These seal-style verified icons appear next to school names across the app.

## Current files

| File | Plan tier | Color |
|------|-----------|-------|
| `verified-basic.svg` | Basic | Green |
| `verified-premium.svg` | Premium | Blue |
| `verified-premium-plus.svg` | Premium Plus | Golden yellow |

Free trial schools do **not** show a badge.

## Replace with your own artwork

1. Create three square images with a **transparent background**.
2. Recommended size: **32×32 px** (or **64×64 px** for retina).
3. Design: small round seal with **wavy/scalloped edges** and a **white tick** in the center (similar to X / Meta verified marks).
4. Save using the **exact filenames** above.
5. Supported formats: `.svg` (best), `.png`, or `.webp`.
6. Drop the files into this folder:

```
frontend/public/assets/badges/
```

7. If you use `.png` instead of `.svg`, update paths in:

```
frontend/src/utils/planBadge.js
```

Change `badgeSrc` values from `.svg` to `.png` for the tiers you replaced.

8. Restart the Vite dev server (`npm run dev`) or rebuild (`npm run build`) so new assets load.

## Quick PNG export tips (Figma / Photoshop / Canva)

- Canvas: 32×32 or 64×64
- Export with transparency enabled
- Keep the tick centered and bold enough to read at 18px display size
- Avoid thin outlines; they disappear on small screens

## Optional @2x set

For sharper displays you may add:

- `verified-basic@2x.png` (64×64)
- `verified-premium@2x.png`
- `verified-premium-plus@2x.png`

Then wire `srcSet` in `PlanVerifiedBadge.jsx` if you want retina support.