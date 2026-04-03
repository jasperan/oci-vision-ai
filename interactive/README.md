# Interactive Explorer

The `interactive/` app is the learn-by-play textbook for OCI Vision AI. It is a static-exportable Next.js app that covers all eight sections from the main README.

## Local development

```bash
cd interactive
npm ci
npm run dev
```

Open the local URL printed by Next.js, typically `http://localhost:3000`.

## Production-style build

```bash
cd interactive
npm ci
npm run build
npm run lint
npm run verify:export
```

The static export is written to `interactive/out/` and is what GitHub Pages publishes. `npm run verify:export` performs a zero-dependency smoke check against the generated `out/index.html`.

## What to verify manually

- Sticky section navigation works.
- Each widget renders without console/build errors.
- The static export exists at `interactive/out/index.html`.
- `npm run verify:export` passes after the build.
- The generated app still works with the repo root walkthrough script:

```bash
bash scripts/readme_walkthrough.sh
```
