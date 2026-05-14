# Mehndi stack reference and Tattoo-Ai reuse decision

**Purpose:** Single place to align the Tattoo Advisor app with the proven **MehndiAI** implementation on disk.

**Mehndi codebase (reference):** `C:\Users\airkooled\Desktop\m\` (sibling project; paths below are relative to that folder).

---

## What Mehndi actually uses in production

| Layer | Implementation |
| --- | --- |
| API | FastAPI `POST /api/generate-ai` — upload photo + `style` + `hand_side` → **JPEG** response (`m\backend\app\routes.py`) |
| AI | **`prunaai/p-image-edit`** on Replicate: **image edit**, not raw txt2img (`m\backend\app\pipeline\replicate_api.py`) |
| Input | User photo as base64 data URI + one **long, structured prompt** |
| Uniqueness | **Random seed** + **per-style random prompt blocks** (layout/motif variations) on every request |
| Client | Next.js: client-side resize, `FormData`, `X-Device-ID`, long timeout (`m\frontend\src\lib\api.ts`) |

**Batch scripts** (`generate_mehndi_flux.py`, `generate_mehndi_imagen.py`) are **separate**: they generate **black-on-white** catalog art via FLUX / Imagen txt2img. They are **not** the live “henna on my hand” path.

---

## Locked decision for Tattoo-Ai

**We will use the same class of approach as Mehndi: an image-edit model that applies the tattoo directly onto the user’s skin in the photo**, with **body placement** and **composition** controlled primarily by **prompting** (plus the same kind of **seed + variation** pattern for uniqueness).

- **Placement:** Generalize Mehndi’s “hand side / palm vs back” logic to **body region** (and optional pose hints) in the edit prompt—e.g. forearm, upper arm, shoulder, calf, etc.
- **Uniqueness:** Same pattern as Mehndi: **different seeds** and **randomized sub-prompts** per concept so each run yields distinct layouts (2–3 parallel or sequential jobs for 2–3 concepts).
- **Visual language:** Swap henna-specific rules (brown stain, mehndi motifs) for **tattoo-specific** rules (black/grey ink, line weight, style tags from [PRODUCT_SPEC.md](PRODUCT_SPEC.md)), while keeping **preserve skin, background, lighting** and **no floating sticker** instructions analogous to Mehndi.

You may still add **LLM** to turn flow answers into these prompts and to generate **fit copy**; the **on-photo preview** can stay **one edit call per concept** like Mehndi.

---

## Optional later paths (not the primary bet)

- **Txt2img** isolated flash + **manual or semi-auto compositing** — useful for artist exports or A/B, but **not** required if image-edit quality is good enough.
- **Segmentation / landmarks** — optional refinement for default placement boxes before edit, or post-check for fit scoring.

---

## Files to read when implementing

1. `m\backend\app\pipeline\replicate_api.py` — prompt templates, variation functions, Replicate HTTP + polling.
2. `m\backend\app\routes.py` — image preprocessing, credits, response headers.
3. `m\frontend\src\lib\api.ts` — client upload contract.

---

## Companion docs in this repo

- [PRODUCT_SPEC.md](PRODUCT_SPEC.md) — product requirements.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — phases and system design (updated to match this decision).
