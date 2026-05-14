# Tattoo Advisor (MVP scaffold)

AI-assisted tattoo **preview** on your body photo using the same **image-edit** pattern as [MehndiAI](MEHNDI_ARCHITECTURE.md) (`prunaai/p-image-edit` on Replicate).

**Docs:** [PRODUCT_SPEC.md](PRODUCT_SPEC.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## Prerequisites

- Python 3.11+
- Node 20+
- [Replicate](https://replicate.com) API token with access to `prunaai/p-image-edit`

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # add REPLICATE_API_TOKEN
python run.py
```

API: `http://localhost:8000` — `POST /api/generate`, `GET /api/ai-status`, `GET /docs`.

## Frontend

```bash
cd frontend
npm install
copy .env.local.example .env.local   # optional: NEXT_PUBLIC_API_URL
npm run dev
```

App: `http://localhost:3000`

## Defaults: one Replicate call per “Generate”

The UI requests **`num_concepts=1`** first. **“Add one more variation”** runs another single call and appends. This keeps latency and cost predictable.

## Production hardening (backend)

- **Rate limits:** `slowapi` per client IP (`GENERATE_RATE_LIMIT`, `STATUS_RATE_LIMIT`). Many replicas ⇒ multiply effective limits; use a shared store (Redis) or enforce at **API gateway / CDN** for strict global caps.
- **Uploads:** Max size (`MAX_UPLOAD_MB`), chunked read, Pillow decode + resize (decompression bomb guard via `Image.MAX_IMAGE_PIXELS`).
- **JSON:** `answers_json` max size (`MAX_ANSWERS_JSON_BYTES`).
- **Optional API key:** `REQUIRE_API_KEY=true` + `TATTOO_SERVICE_KEY` + header `X-API-Key`. For public web, prefer the **Next.js BFF** (`frontend/app/api/tattoo/generate/route.ts`) so the key never ships to the browser; set `TATTOO_BACKEND_URL` and `TATTOO_SERVICE_KEY` on the Next server and `NEXT_PUBLIC_USE_BFF=1` in the client env.
- **Scale:** Stateless API + horizontal pods; move Replicate calls to a **job queue** if you need back-pressure at very high load.

## Disclaimer

Outputs are **visual simulations** for planning only — not medical advice. Consult a professional artist before getting tattooed.
