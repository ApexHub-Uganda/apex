# Mobile showcase images — “Power in Every Pocket”

The landing page **Mobile Experience** section displays PNG screenshots from this folder. Replace any file below to update the site without touching React code.

## Current files

| File | Slot label | Used on |
|------|------------|---------|
| `parent-portal.png` | Parent Portal | Landing → Power in Every Pocket |
| `teacher-portal.png` | Teacher Portal | Landing → Power in Every Pocket |
| `student-portal.png` | Student Portal | Landing → Power in Every Pocket |
| `finance-app.png` | Finance App | Landing → Power in Every Pocket |

Paths are served from:

```
frontend/public/landing/mobile/
```

Public URL prefix: `/landing/mobile/`

## Replace with your own PNGs

1. Export **portrait** mobile screenshots (phone UI or mockups).
2. Recommended size: **360×780 px** (or any 9∶19.5 ratio, e.g. 390×844).
3. Format: **PNG** (JPG/WebP also work if you update paths in config).
4. Keep the **exact filenames** in the table above, or add new slots (see below).
5. Overwrite the file in this folder — same name replaces the old image.
6. Hard-refresh the browser (Ctrl+F5) or restart `npm run dev` if the old image is cached.

### Design tips

- Use a consistent device frame or clean full-bleed screenshots across all four slots.
- Crop from the **top** of the screen; the layout uses `object-fit: cover` and `object-position: top`.
- Avoid very wide images; portrait ratio keeps the grid balanced on desktop.

## Add or rename a slot

1. Drop the new PNG in this folder.
2. Edit `MOBILE_APPS` in:

   ```
   frontend/src/pages/landing/landingData.js
   ```

   Example entry:

   ```js
   {
     id: 'admin-app',
     name: 'Admin App',
     image: `${MOBILE_SHOWCASE_IMAGE_DIR}/admin-app.png`,
     alt: 'School admin mobile app screenshot',
   }
   ```

3. Rebuild or refresh the dev server.

## Remove a slot

Delete the item from `MOBILE_APPS` in `landingData.js`. You may leave the unused PNG in this folder.

## Placeholder images

The bundled PNGs are **temporary placeholders** (“Replace with your PNG”). Swap them whenever you have final marketing screenshots.

## Related code

| File | Purpose |
|------|---------|
| `frontend/src/pages/landing/landingData.js` | `MOBILE_APPS` image paths and captions |
| `frontend/src/components/landing/LandingSections.jsx` | `LandingMobile` section markup |
| `frontend/src/pages/landing/landing.css` | `.lp-mobile-shot*` layout styles |