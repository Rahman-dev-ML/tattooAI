"""
Tattoo motif libraries, theme libraries, region anatomy zones, and intensity presets.

Mirrors the architecture of the Mehndi project (m/backend/app/pipeline/replicate_api.py):
- Per-style libraries of CONCRETE artist motifs (the model needs real names, not descriptions).
- Per-theme libraries (15-20 motifs per theme) so meaning-driven flows pick from a deep well.
- Region anatomy zones — generic placement notes that style templates compose into briefs.
- Intensity presets — replaces the old conflicting coverage/strength rule blocks.

Every list is intentionally rich (15-30+ items) so concept variations feel meaningfully
different on every "Add another variation" call.
"""
from __future__ import annotations

from random import Random
from typing import Optional


# =====================================================================================
# REGION ANATOMY ZONES
# Generic anatomy notes that every style template uses inside its PLACEMENT zone.
# Style templates can also overlay their own style-aware notes (e.g. Japanese on forearm
# emphasizes "irezumi flow along the limb axis").
# =====================================================================================

REGION_ANATOMY: dict[str, str] = {
    "forearm": (
        "FOREARM SURFACE — outer or inner forearm skin visible in this photo. "
        "Cylindrical limb with tendon and muscle ridges. The tattoo MUST wrap with the "
        "natural muscle curvature, not lay flat like a sticker. Long axis of the design "
        "runs along the limb (wrist → elbow). Edges of the design follow the limb contour, "
        "tapering naturally where skin curves away from camera."
    ),
    "upper_arm": (
        "UPPER ARM / BICEP — rounded cylindrical arm skin. Strong perspective wrap because "
        "of the muscle swell. Design follows the bicep contour, with the visible side rendered "
        "sharp and the edges foreshortening as they curve around the arm. Major axis runs "
        "along arm length."
    ),
    "shoulder": (
        "SHOULDER / DELTOID CAP — rounded shoulder dome. Design wraps over the cap curvature "
        "with edges foreshortening into the back/chest transitions. The natural cap shape gives "
        "the composition a circular or fan-like silhouette."
    ),
    "wrist": (
        "WRIST / LOWER FOREARM — narrow transition between forearm and hand. Bone ridge "
        "visible. Small scale only. Design follows the wrist crease and bone structure. "
        "Reads cleanly even at small size."
    ),
    "hand_back": (
        "BACK OF HAND / DORSUM — knuckles, tendons, and metacarpal ridges visible. Small to "
        "medium scale. Design respects knuckle creases and tendon valleys. No design crosses "
        "joint lines without a deliberate break."
    ),
    "calf": (
        "CALF — calf muscle belly visible with vertical curvature. Vertical compositions read "
        "best (long axis runs ankle → knee). Ink wraps around the calf curve. Substantial real "
        "estate available."
    ),
    "thigh": (
        "THIGH — large flat-ish surface with quad curvature. Room for a medium-to-large piece. "
        "Design follows quad muscle shape and wraps slightly at the outer edges."
    ),
    "chest": (
        "CHEST / PEC — pec muscle shape and sternum centerline visible. Design respects the "
        "centerline (no drift onto sternum unless intentional double-sided composition). Sits "
        "naturally on the pec surface with subtle wrap toward the armpit."
    ),
    "upper_back": (
        "UPPER BACK — broad flat canvas between scapulae. Spine line is the centerline. Design "
        "either sits one side of the spine OR uses the spine as a symmetry axis."
    ),
    "ribs": (
        "RIBS / FLANK — rib lines visible, thin skin. Conservative detail. Design follows rib "
        "curvature and wraps with the flank. Avoid heavy fills here."
    ),
    "ankle": (
        "ANKLE / LOWER SHIN — ankle bone contour and lower shin visible. Small scale. Reads "
        "cleanly at small size. Design either wraps the ankle OR sits above it on the shin."
    ),
    "neck": (
        "NECK SIDE / NAPE — narrow visible neck skin. Conservative scale. Design follows the "
        "neck curve. Vertical compositions read best."
    ),
    "other": (
        "VISIBLE SKIN AREA — the main visible skin region in this photo. Infer correct "
        "anatomy. Wrap design with body curvature."
    ),
    "from_photo": (
        "BODY AREA IN THIS EXACT PHOTO — read the visible anatomy. Place tattoo on the actual "
        "skin area shown. Tattoo aligns to real skin: wraps with curvature, perspective, and "
        "the lighting already present in the photo."
    ),
}


# =====================================================================================
# INTENSITY PRESETS
# Replaces the old coverage + strength dual inputs. One preset = one self-consistent
# composition target. Mehndi worked because bridal IS dense and eid IS airy — the style
# itself implies coverage. We do the same: pick an intensity, get a coherent piece.
# =====================================================================================

INTENSITY_PRESETS: dict[str, dict[str, str]] = {
    "whisper": {
        "label": "Whisper",
        "coverage_pct": "5 to 12 percent of visible skin",
        "scale": "very small — 2 to 5 cm dimension",
        "directive": (
            "*** INTENSITY: WHISPER ***\n"
            "Almost-not-there tattoo. ONE element only. 2 to 5 cm maximum dimension. "
            "85+ percent of visible skin stays completely bare. Hair-thin lines, minimal or zero "
            "shading. The piece reads like a personal secret on the skin. If unsure, go SMALLER."
        ),
        "element_count": "ONE single element",
        "linework_bias": "hair-thin (1RL needle quality)",
    },
    "personal": {
        "label": "Personal",
        "coverage_pct": "12 to 25 percent of visible skin",
        "scale": "small to medium — 5 to 10 cm dimension",
        "directive": (
            "*** INTENSITY: PERSONAL ***\n"
            "Clear, considered tattoo with breathing room. ONE main focal at 5 to 10 cm, "
            "optionally with ONE small accent element 2 to 4 cm placed nearby. Generous bare "
            "skin around the composition. Mixed line weights allowed. Light shading where it "
            "serves the design."
        ),
        "element_count": "one focal (+ optional one small accent)",
        "linework_bias": "mixed: thinner interior, slightly bolder main contour",
    },
    "commanding": {
        "label": "Commanding",
        "coverage_pct": "25 to 40 percent of visible skin",
        "scale": "medium to large — 10 to 16 cm dimension",
        "directive": (
            "*** INTENSITY: COMMANDING ***\n"
            "Statement piece with confident presence. Main focal at 10 to 16 cm with 1 to 3 "
            "supporting elements integrated into one cohesive composition. Bold outlines on "
            "main contours. Intentional shading where it adds depth. Negative space is planned, "
            "not residual. Reads as a real artist's piece, not generic flash."
        ),
        "element_count": "one focal + 1 to 3 integrated supporting elements",
        "linework_bias": "bold confident main contours with finer interior detail",
    },
    "centerpiece": {
        "label": "Centerpiece",
        "coverage_pct": "40 to 65 percent of visible skin",
        "scale": "large — 16 to 24 cm dimension",
        "directive": (
            "*** INTENSITY: CENTERPIECE ***\n"
            "Dominant tattoo composition. Multi-element piece with a clear hero subject and "
            "supporting elements that flow into one another. Full range of line weights and "
            "shading. Negative space is carved with intent — the design and the bare skin both "
            "do work. This is the body part's signature ink."
        ),
        "element_count": "hero subject + 2 to 5 integrated supporting elements forming one composition",
        "linework_bias": "full range — bold outer contours, fine interior, planned shading zones",
    },
}


# =====================================================================================
# UNIVERSAL SKIN REALISM BLOCK
# Appended to every prompt. The single most important block for killing the
# "sticker / decal / clip-art" failure mode.
# =====================================================================================

SKIN_REALISM = """
NO TEXT RULE (ABSOLUTE): Zero letters, zero words, zero numbers, zero readable characters anywhere in the tattoo design unless this is a script-style piece. Pure visual symbol only. If ANY accidental text appears, the output has failed.

SKIN AND INK REALISM (CRITICAL):
- This is a REAL TATTOO on REAL HUMAN SKIN. Ink sits IN the dermis — not painted on top, not floating above the skin.
- Skin pores, hair follicles, freckles, fine skin texture remain VISIBLE THROUGH and AROUND the ink.
- The tattoo has a HEALED look: matte, slightly settled, natural micro-oxidation in the darker areas.
- Ink edges have a faint organic softness and micro-bleed — NOT laser-sharp vector edges.
- Room lighting and shadows in the photo wrap OVER the tattoo naturally. Highlights of the original photo show across the ink.
- DO NOT smooth the skin. DO NOT plastic-ify it. Preserve the original skin tone and texture exactly.
- The design follows the body curvature — wraps with the skin, never pasted flat like a decal.
- NOT a sticker. NOT clip art. NOT a badge. NOT a logo. NOT a stamp. NOT a patch. NOT a printed transfer.
- A casual viewer must believe this is a real photo of a tattooed person.
- Keep the EXACT same body, background, clothing, skin tone, and lighting as the original photograph. Only the tattoo is new.
""".strip()


# =====================================================================================
# CONCRETE MOTIF LIBRARIES — per style
# Each is a list of FULL artist phrases ready to be dropped into a prompt as the
# focal subject. Vocabulary matches what real tattoo artists call these things.
# =====================================================================================

MINIMALIST_MOTIFS: list[str] = [
    "single-line continuous botanical sprig — 3 to 5 leaves on one thin stem, no lifting of the pen",
    "single-line silhouette of a small bird mid-flight, one continuous gesture",
    "tiny constellation — 4 to 6 micro dots connected by hair-thin lines forming a recognizable shape",
    "thin-line crescent moon with one small dot of negative space inside",
    "one small mountain range silhouette — two or three continuous peaks, single line",
    "tiny solid-line triangle (equilateral) with one micro dot at the apex",
    "minimal arrow — thin shaft with a small flared tip",
    "single-line wave — Hokusai-style stylized curl reduced to one continuous stroke",
    "tiny solid heart outline (2cm) with one micro dot to the side",
    "minimalist sun — thin circle with 6 short rays at compass points",
    "single-line silhouette of a cat sitting in profile, one stroke",
    "tiny anchor — clean thin lines, no shading, classic proportions at small scale",
    "thin-line pine tree triangle — single outline with one inner trunk line",
    "minimalist eye — thin almond outline with a single dot pupil",
    "tiny lightning bolt — clean angular thin stroke",
    "minimal infinity loop — single continuous line",
    "tiny envelope outline — clean rectangle with the V flap line, 2 to 3 cm",
    "minimal compass — thin circle with 4-point cardinal star inside",
    "single-line silhouette of a butterfly — one continuous stroke for both wings",
    "tiny crescent moon and three dot stars in a small arc",
]

FINE_LINE_MOTIFS: list[str] = [
    "fine-line single rose — open petals with delicate interior fold lines, hair-fine contour, 5 to 8 cm",
    "fine-line peony — layered petals with elegant micro-shading inside two petals only, 6 to 9 cm",
    "fine-line botanical branch — eucalyptus or olive, 5 to 8 leaves on a thin curving stem",
    "fine-line wildflower bouquet — three flower types loosely tied, no ribbon",
    "fine-line snake — flowing S-curve body with tiny scale suggestion marks along the back",
    "fine-line butterfly — symmetrical wings with delicate vein lines, no fill",
    "fine-line hummingbird in flight, wings extended, hair-thin feather indications",
    "fine-line ocean wave with tiny dotwork foam at the crest",
    "fine-line celestial composition — crescent moon with three stars and a dotted meridian line",
    "fine-line lavender sprig — three flower clusters on a single thin stem",
    "fine-line dragonfly — symmetric wings with the lightest interior vein web",
    "fine-line crane in profile, one leg lifted, fine feather indication on the wing only",
    "fine-line lily — single bloom with three visible petals and one curling leaf",
    "fine-line bee — small body, fine wing outlines, three legs visible",
    "fine-line cherry branch — five blossoms, two falling, thin branch",
    "fine-line phases of the moon row — 5 phases on a thin baseline",
    "fine-line jellyfish — bell with three trailing tendrils, hair-fine",
    "fine-line mountain horizon — three layered ridges with a tiny sun behind, no fill",
    "fine-line constellation map — Orion or Cassiopeia, dots connected by thread-thin lines",
    "fine-line poppy — open bloom with bee tucked into one petal",
    "fine-line ginkgo leaf — fan shape with delicate radiating vein lines",
    "fine-line sword and rose — slim sword vertical, single rose entwined at the hilt",
    "fine-line fern frond — single curving stem with paired leaflets",
    "fine-line magnolia bloom — single open flower with two leaves",
    "fine-line snake coiled around a delicate dagger, no fill",
]

BLACKWORK_MOTIFS: list[str] = [
    "bold blackwork wolf head silhouette — solid black with planned negative skin windows for eyes and snout detail",
    "bold blackwork raven in flight — solid black silhouette with negative-space wing feather lines",
    "bold blackwork bear head — solid mass with negative-space muzzle and eye details",
    "blackwork mandala fragment — quarter or half mandala in solid black with intentional skin windows for the rays",
    "blackwork botanical — solid black rose silhouette with negative-space petal vein lines",
    "blackwork leaf cluster — three large leaves in solid black with negative-space stem and vein detail",
    "blackwork sacred geometry — solid black hexagram with carved skin-window triangles",
    "blackwork ouroboros — solid black snake forming a closed circle, scale suggestions in negative space",
    "blackwork moth — solid black silhouette with negative-space wing pattern (death's head style)",
    "blackwork dagger — bold solid black blade with negative-space detail at the guard",
    "blackwork all-seeing eye — bold triangle in solid black with negative-space iris and rays",
    "blackwork crescent moon — solid black crescent with carved negative-space stars inside",
    "blackwork chest band fragment — bold solid black band with planned skin-window cutouts",
    "blackwork stag skull — solid black skull with negative-space antler lines",
    "blackwork sword and serpent — solid black sword with serpent coiling around it in negative space",
    "blackwork floral mandala — solid black petals radiating with carved skin gaps",
    "blackwork hand of fatima / hamsa — solid black with negative-space interior detail",
    "blackwork wave fragment — solid black Japanese wave with negative-space foam curls",
    "blackwork triangle composition — three nested triangles in solid black with skin-window interior",
    "blackwork panther head — bold silhouette with negative-space eye and fang detail",
    "blackwork mountain silhouette — solid black peaks with negative-space sun rising behind",
    "blackwork crow with key — solid black crow holding a small skeleton key (negative-space teeth)",
]

TRADITIONAL_MOTIFS: list[str] = [
    "classic American traditional rose — chunky petals, thick black outline, red and green flat fill suggested through linework only (B&G rendering)",
    "traditional swallow in flight — wings spread, bold outline, classic teardrop body, banner curling below",
    "traditional dagger through a rose — straight blade, ornamental hilt, single rose pierced",
    "traditional skull with crossbones — bold outline, classic shading blocks, no extra ornament",
    "traditional flaming heart — bold heart with three flames rising, scroll banner at base",
    "traditional eagle head — fierce outward profile, bold feather outlines, beak open",
    "traditional anchor with rope — classic shape, rope coiled around the shaft, banner at base",
    "traditional snake coiled — bold outline, defined scales, fangs visible, classic flash style",
    "traditional panther head — snarling profile, bold whiskers, classic American flash",
    "traditional pin-up sailor girl — head and shoulders only, classic 1940s style",
    "traditional ship in full sail — bold outline, water lines below, banner above",
    "traditional rose and dagger composite — rose at center, dagger vertical behind",
    "traditional butterfly — bold symmetric wings, classic interior pattern",
    "traditional black cat with arched back — Halloween flash style, bold outline",
    "traditional sacred heart — heart with rays, crown of thorns, drops at base",
    "traditional tiger head — fierce profile, bold stripes, classic flash",
    "traditional hand of glory — candle in hand, bold flame, classic occult flash",
    "traditional chest banner — bold scroll spanning the area, decorative ends",
    "traditional clipper ship — full mast, waves below, sky lines above",
    "traditional swallow pair facing each other with a shared rose between",
    "traditional praying hands with rosary — classic religious flash",
    "traditional anatomical heart — bold outline, classic shading blocks",
    "traditional skull with rose in mouth — bold composition, classic flash",
]

SCRIPT_MOTIFS: list[str] = [
    "single short word in flowing English cursive — graceful connected letters with thick-thin variation",
    "short two-word phrase in elegant serif italic — formal classical proportions",
    "single word in clean modern sans-serif — even weight, contemporary",
    "Roman numeral date in classic serif capitals — meaningful date, formal",
    "single word in calligraphic gothic blackletter — heavy formal lettering",
    "two lines of poetry in delicate handwritten cursive — natural rhythm, slight wobble",
    "single phrase in old-school traditional tattoo lettering — bold serif with flair",
    "Arabic calligraphy phrase — flowing connected script (only if user provides text)",
    "single word in Japanese kanji — bold brushstroke style (only if user provides character)",
    "Hindi or Sanskrit word in Devanagari script — formal proportions (only if user provides text)",
    "Hebrew word — square Torah-style letters (only if user provides text)",
    "Greek word in classical capital style (only if user provides text)",
    "name in graceful signature-style cursive — personal handwriting feel",
    "verse in 'sailor jerry' bold traditional script with banner ends",
    "single italic word with one small ornamental flourish from the last letter",
    "music notation fragment — bar of melody on a thin staff (no lyrics)",
    "Morse code word — dots and dashes on a thin baseline",
]

GEOMETRIC_MOTIFS: list[str] = [
    "Sri Yantra — precise nested triangulations with central bindu, 6 to 9 cm",
    "geometric wolf head — built from triangulated facets and clean angular planes",
    "geometric deer or stag head — antlers as branching geometric arms, faceted face",
    "geometric mandala — concentric rings with angular radial divisions, dotwork at vertices",
    "Flower of Life — overlapping circles in precise grid, 7 to 10 cm",
    "geometric bear head — solid mass built from clean angular facets",
    "Metatron's cube — sacred geometry with all 13 spheres connected",
    "platonic cube in clean line perspective — depth illusion via line weight",
    "tetrahedron rendered in clean lines — 3D form via thin internal lines",
    "geometric eye — eye shape built from triangulations and concentric rings",
    "geometric lotus — petals as triangulated facets in radial symmetry",
    "geometric mountain range — peaks as clean triangles with internal hatch lines",
    "Penrose triangle — impossible figure in clean line, 5 to 7 cm",
    "geometric phoenix — bird form built from angular facets, rising posture",
    "dotwork mandala — concentric rings entirely composed of measured single dots",
    "geometric fox head — sharp angular planes forming the muzzle and ears",
    "geometric celestial composition — nested moon phases inside concentric circles",
    "geometric serpent — triangulated body coiled in a precise spiral",
    "geometric rose — petals constructed from sharp triangular facets",
    "geometric whale tail breaching from clean triangulated waves",
    "geometric tree of life — branches as branching line segments, roots mirroring",
    "geometric raven — silhouette built from sharp angular planes",
]

ORNAMENTAL_MOTIFS: list[str] = [
    "central medallion with radiating filigree branches and chandelier teardrop drops, 6 to 10 cm",
    "ornamental crescent moon with hanging chandelier teardrops below",
    "baroque cartouche — ornate oval frame with empty interior negative space",
    "ornamental band fragment — filigree connections at both ends, lace-like center",
    "ornamental jewel-like medallion with bead chain edge and central rosette",
    "ornamental dreamcatcher — geometric web inside an ornate ring with hanging filigree",
    "ornamental anatomical heart — heart wrapped in baroque scrollwork",
    "ornamental keyhole — vintage keyhole shape with filigree surround",
    "ornamental hand of fatima — filigree interior, lace-like edge, no solid fill",
    "ornamental Victorian frame — ornate oval frame with hanging beadwork",
    "ornamental snake coiled around ornate cross — filigree details on the cross",
    "ornamental mandala chest piece — radial symmetric, jewelry-like, lace interior",
    "ornamental compass rose — central star inside an ornate filigree ring",
    "ornamental skeleton key — ornate filigree handle, decorative bow",
    "ornamental fan — Victorian fan shape with filigree spokes",
    "ornamental moth — wings filled with baroque filigree pattern instead of solid black",
    "ornamental anchor — anchor with filigree wrapping around the shaft",
    "ornamental stag skull — antlers detailed with filigree branches",
    "ornamental crown — small ornate crown with bead chain and filigree points",
    "ornamental rose mandala — rose at center, filigree petals radiating outward",
]

JAPANESE_MOTIFS: list[str] = [
    "koi fish ascending — dynamic upward swim posture, suggested scale texture, fins showing movement, 8 to 14 cm",
    "koi fish descending — flowing downward swim with cherry blossoms drifting around",
    "Japanese dragon fragment — head and forepaws emerging from cloud or mist, scale suggestion",
    "tiger crouching low — Japanese irezumi tiger with bold stripes and cherry blossoms",
    "phoenix in flight — wings extended, tail trailing flames, classical irezumi proportion",
    "cherry blossom branch — 4 to 6 blooms in various stages, 2 falling petals drifting",
    "chrysanthemum in full bloom — tightly layered petals, classical irezumi rendering",
    "Japanese wave (Hokusai-inspired) — cresting wave with structured foam, dramatic curl",
    "maple leaf cluster — 3 to 5 leaves in autumn configuration, falling with the wind",
    "crane in flight — wings extended in classical Japanese proportion, single leg trailing",
    "snake coiled — Japanese snake with traditional scale work, S-curve body",
    "hannya mask — traditional Noh demon mask, intense expression, classical proportion",
    "foo dog (lion-dog) seated — guardian figure, traditional irezumi rendering",
    "geisha portrait fragment — head and shoulders, hair pin, classical proportions",
    "samurai mask (mempo) — traditional helmet face guard with fierce expression",
    "lotus rising from waves — bloom emerging from cresting Japanese water",
    "kitsune (fox) with multiple tails — mythological fox in classical pose",
    "tengu mask — long-nosed mountain spirit mask, traditional rendering",
    "Japanese skull (dokuro) — stylized irezumi skull with cherry blossoms",
    "peony in bloom — traditional Japanese peony with bold petals and curling leaves",
    "carp jumping the dragon gate — koi mid-leap with waterfall lines",
    "shishi lion guardian head — fierce mane, traditional stylization",
    "dragon and tiger composition (ryu-tora) — facing each other, classical pairing",
]

REALISM_MOTIFS: list[str] = [
    "photorealistic rose — full bloom with believable petal layers, dewdrop, controlled B&G shading",
    "photorealistic lion portrait — frontal face, detailed mane texture, intense eyes",
    "photorealistic wolf portrait — three-quarter view, fur direction visible, soulful eyes",
    "photorealistic human eye — detailed iris striations, lash texture, tear duct, single tear",
    "photorealistic vintage pocket watch — worn metal texture, visible gears, chain trailing",
    "photorealistic compass — antique brass texture, glass face, needle pointing N",
    "photorealistic feather — individual barb texture, soft falloff at edges, light source consistent",
    "photorealistic skull — bone texture, anatomical accuracy, B&G shading with deep contrast",
    "photorealistic dog portrait — breed-specific features, fur texture, expressive eyes",
    "photorealistic hands in prayer — anatomical accuracy, skin folds, rosary draped",
    "photorealistic mountain range with mist — dramatic depth, atmospheric perspective",
    "photorealistic raven portrait — feather texture, intelligent eye, beak detail",
    "photorealistic anatomical heart — accurate musculature, vessel detail, B&G",
    "photorealistic religious figure portrait — Christ, Mary, or saint with classical art reference",
    "photorealistic tiger portrait — full face, stripe pattern accurate, intense gaze",
    "photorealistic owl portrait — feather pattern detailed, large eyes, talons gripping branch",
    "photorealistic galaxy — swirling stars and nebula in B&G with depth",
    "photorealistic clock face — Roman numerals, hands at meaningful time, weathered face",
    "photorealistic rose with thorns — single bloom on thorny stem, dewdrops",
    "photorealistic eagle in flight — feather detail, sharp eye, talons extended",
    "photorealistic vintage camera — leather texture, brass detail, worn lens",
    "photorealistic hourglass — sand mid-fall, glass reflections, wood frame",
]

# Auto draws from the most-applicable adjacent style based on context.
AUTO_FALLBACK_MOTIFS: list[str] = (
    FINE_LINE_MOTIFS[:8]
    + BLACKWORK_MOTIFS[:6]
    + TRADITIONAL_MOTIFS[:6]
    + GEOMETRIC_MOTIFS[:4]
    + JAPANESE_MOTIFS[:4]
)


STYLE_MOTIFS: dict[str, list[str]] = {
    "minimalist": MINIMALIST_MOTIFS,
    "minimal": MINIMALIST_MOTIFS,
    "fine_line": FINE_LINE_MOTIFS,
    "blackwork": BLACKWORK_MOTIFS,
    "stencil": BLACKWORK_MOTIFS,
    "traditional": TRADITIONAL_MOTIFS,
    "script": SCRIPT_MOTIFS,
    "geometric": GEOMETRIC_MOTIFS,
    "ornamental": ORNAMENTAL_MOTIFS,
    "japanese": JAPANESE_MOTIFS,
    "realism": REALISM_MOTIFS,
    "realistic": REALISM_MOTIFS,
    "auto": AUTO_FALLBACK_MOTIFS,
}


# =====================================================================================
# THEME LIBRARIES — for new_to_tattoos and deep_meaning
# 15-20 concrete subject phrases per theme. Each phrase is a complete artist motif
# ready to be a focal subject (NOT a generic descriptor like "small lion silhouette").
# =====================================================================================

THEME_MOTIFS: dict[str, list[str]] = {
    "strength": [
        "lion head in three-quarter profile with detailed mane suggestion, calm and powerful",
        "single mountain peak with snow line — strong silhouette, vertical thrust",
        "compact oak tree with strong trunk and rounded canopy, deep root suggestion",
        "stag head with antlers spreading wide — proud upright posture",
        "anchor with rope coiled around the shaft — bold classical proportions",
        "bear head in profile — solid presence, calm strength",
        "Norse vegvisir compass — runic strength symbol with eight points",
        "wolf head howling at the moon — strength of the pack",
        "ouroboros — serpent eating its own tail, eternal endurance",
        "Spartan helmet in profile — bold warrior silhouette",
        "rising phoenix with wings spread — strength through rebirth",
        "single closed fist held high — power and resolve",
        "pillars of Hercules — two columns with sun rising between them",
        "elephant in profile with trunk lifted — quiet strength",
        "rhino head in profile — armored strength",
        "single-line bull silhouette with horns lowered — directional power",
    ],
    "faith": [
        "small cross with simple proportions — clean lines, no excess ornament",
        "dove in flight carrying an olive branch — peace and faith",
        "rosary loop with delicate beads forming a circle around a small cross",
        "crescent moon with a single star inside — Islamic faith motif",
        "praying hands with light rays radiating behind — devotion",
        "Star of David in clean thin line — Jewish faith motif",
        "Om symbol in flowing brushstroke — Hindu/Buddhist meditation",
        "ichthys (fish) symbol — early Christian motif, single line",
        "Buddha in lotus seated meditation pose — calm devotion",
        "small chapel silhouette with a cross on the steeple",
        "Madonna and child portrait in classical religious art style",
        "Sacred Heart with crown of thorns and rays — classical religious motif",
        "ankh — Egyptian symbol of life, clean proportions",
        "candle with flame on a small altar — quiet faith",
        "tree of life — branching crown above mirroring roots below",
        "Hand of Fatima (hamsa) with eye in the palm",
        "yin-yang circle in clean thin line — balance and faith",
        "lotus flower in full bloom rising from water — spiritual awakening",
    ],
    "patience": [
        "tortoise in profile silhouette — slow steady ancient",
        "hourglass with sand mid-fall — patience visualized",
        "single bamboo stalk standing upright — patient strength",
        "koi fish swimming upstream — persistence",
        "lotus bud not yet opened — waiting for the right moment",
        "spider on a delicate web — patient craft",
        "sundial with simple face — time passing slowly",
        "snail with elegant spiral shell — slowness as virtue",
        "old oak tree with deep roots and weathered trunk",
        "monk in seated meditation silhouette",
        "crescent moon over still water — quiet waiting",
        "single Japanese pine tree (matsu) — endurance and patience",
        "stone garden ripple pattern in concentric circles",
        "single bonsai tree shaped over decades",
        "candle burning slowly with a long thin flame",
    ],
    "rebirth": [
        "phoenix rising from flames — wings spread upward",
        "butterfly emerging from chrysalis — wings just opening",
        "lotus in full bloom rising from dark water",
        "fern fiddlehead unfurling — coiled and emerging",
        "sunrise behind a single horizon line with rays",
        "snake shedding its skin — coiled body, peeled skin trailing",
        "phoenix feather single — long curved plume with detail",
        "egg cracking open with light emerging",
        "spring tree with first buds appearing on bare branches",
        "single dandelion seed head with seeds blowing away",
        "moth emerging from cocoon — wings drying",
        "wave breaking and reforming — cyclical motion",
        "ouroboros — eternal cycle of death and rebirth",
        "seedling sprout pushing through earth — first leaves visible",
        "moon phases row — new to full to new again",
        "salmon leaping upstream toward spawning ground",
    ],
    "healing": [
        "lavender sprig — three flower clusters on a single thin stem",
        "small heart with a delicate kintsugi gold-crack line through it",
        "eucalyptus branch with five rounded leaves on a thin stem",
        "crescent moon with healing light suggestion",
        "aloe vera leaf — single bold medicinal leaf",
        "snake coiled around a staff — caduceus / Asclepius symbol",
        "hands cupping a small flower — gentle care",
        "single white lily — purity and healing",
        "bee on a flower — pollination and renewal",
        "willow tree with drooping branches — healing tears",
        "chamomile flower with petals open — calming",
        "small cross of two leaves — natural healing",
        "rose of Sharon in bloom — sacred healing flower",
        "feather floating downward — gentle peace",
        "moon and sun in balance — restored equilibrium",
        "small bandaged hand opening to release a butterfly",
    ],
    "love": [
        "two intertwined hearts in continuous single line",
        "infinity loop with a small heart at the crossing point",
        "single rose bud just opening — petals unfurling",
        "lock and key placed close together — locked love",
        "pair of small birds perched on a single branch",
        "two hands almost touching (Michelangelo reference) in fine line",
        "anatomical heart with a vine of roses growing from it",
        "two cranes facing each other in classical Japanese pairing",
        "Cupid's arrow through a single heart",
        "claddagh ring — heart in hands with crown above",
        "two doves with a shared olive branch between them",
        "padlock with two initials inside in delicate script",
        "single red string of fate connecting two small hearts",
        "two koi fish circling in yin-yang formation",
        "Eros and Psyche silhouettes embracing",
        "couple of butterflies dancing around a single flower",
    ],
    "family": [
        "tree of life — branching crown above with mirrored roots",
        "linked chain of three rings — generations bound",
        "three birds in flight ascending together",
        "small house with a warmly suggested chimney smoke",
        "deep roots spreading below a short sturdy trunk",
        "pair of adult hands cradling smaller hands inside",
        "compass rose with each cardinal point as a small symbol",
        "wolf pack silhouette — alpha with cubs trailing",
        "single oak tree with multiple branching arms",
        "constellation of family members as connected stars",
        "elephant family in profile — adult and calf",
        "bird's nest with three small eggs",
        "umbrella sheltering small figures beneath",
        "intertwined initials in elegant calligraphy",
        "family of cranes — adults and chick walking together",
    ],
    "discipline": [
        "small compass rose with N/S/E/W marks in clean circular frame",
        "katana sword vertical — clean blade, minimal guard, tsuba detail",
        "chess knight piece in profile — strategic and sharp",
        "shield with heraldic shape — clean and strong",
        "hourglass with visible sand — time and discipline",
        "lighthouse on a cliff — steadfast guidance",
        "Spartan helmet in profile — warrior discipline",
        "pen and sword crossed — discipline of mind and body",
        "samurai bow (yumi) drawn — focus and discipline",
        "labyrinth circle — single path inward, focused journey",
        "monk in seated meditation — mental discipline",
        "anchor with chain — steadfast grounding",
        "single arrow released from a bow",
        "pillars of a Greek temple — three columns",
        "dojo entrance gate (torii) — discipline of practice",
    ],
    "freedom": [
        "single bird in soaring flight — wing arc silhouette",
        "dandelion with seeds blowing away on the wind",
        "single feather falling — light, drifting downward",
        "open birdcage with door ajar and bird flying away",
        "two birds flying away from a branch together",
        "horse mid-gallop with mane flowing — wild freedom",
        "compass rose pointing toward the horizon",
        "balloon released into the sky with string trailing",
        "wave breaking on an open shore — boundless ocean",
        "eagle in soaring flight — wings fully extended",
        "key floating away from broken chains",
        "wolf howling on a mountain peak under stars",
        "phoenix wings spread — freedom through transformation",
        "kite high in the sky with long tail flowing",
        "boat on open water with full sail",
        "running cheetah in mid-stride silhouette",
    ],
    "hope": [
        "lighthouse on a cliff with a beam of light cutting through fog",
        "three small stars in a gentle ascending arc",
        "single candle flame standing upright in darkness",
        "tiny seedling sprout with two first leaves emerging from soil",
        "dove carrying an olive branch in its beak",
        "sunrise behind mountain silhouette with rays radiating",
        "single anchor with rope — hope as anchor of the soul",
        "lotus opening with a single dewdrop on a petal",
        "phoenix rising from ashes with first feather visible",
        "north star with subtle radiating rays",
        "pandora's box with a single moth (hope) flying out",
        "bird perched at the edge of a leaf with one wing lifted",
        "small house with warm light glowing from a single window",
        "tree growing from a crack in a rock — resilience and hope",
        "shooting star with a long thin trail",
    ],
    "peace": [
        "olive branch with five to seven leaves on a curved stem",
        "yin-yang circle in clean thin line",
        "lotus floating on calm water with ripples",
        "peace dove with wings spread in flight",
        "single soft cloud outline — quiet floating",
        "Buddha in lotus seated meditation",
        "zen enso circle — single ink brush stroke forming an open circle",
        "mountain reflected in still lake — perfect calm",
        "small Japanese stone garden ripple pattern",
        "single white lily floating on water",
        "shanti symbol in flowing script",
        "two hands releasing a paper crane",
        "candle with thin flame in still air",
        "torii gate at sunset — peaceful threshold",
        "om symbol in flowing brushstroke",
    ],
    "loss": [
        "willow branch with drooping thin fronds — quiet grief",
        "tiny forget-me-not flower — small, delicate, remembered",
        "single feather falling slowly downward",
        "single candle flame still burning — remembering",
        "angel wing silhouette — single wing, gentle outline",
        "empty rocking chair silhouette",
        "broken chain with one floating link",
        "rose with one petal falling away",
        "moon obscured by passing cloud",
        "small urn with smoke rising in delicate curls",
        "tree losing its last autumn leaf",
        "anchor sinking into deep water",
        "two hands releasing a butterfly",
        "small grave with single flower",
        "phoenix feather burning at the tip",
    ],
    "philosophy": [
        "ouroboros — snake eating its tail, compact circle",
        "open book outline with pages catching the wind",
        "atom symbol with nucleus and orbiting rings",
        "Möbius strip — one continuous twisted loop",
        "labyrinth circle — single inward spiral path",
        "Vitruvian man fragment — outstretched figure in circle",
        "scales of justice in balance",
        "Rodin's Thinker silhouette in fine line",
        "tree of knowledge with serpent coiled in branches",
        "all-seeing eye inside a triangle with rays",
        "infinity loop with a small dot at center",
        "yin-yang circle with a small philosopher's stone",
        "Plato's cave silhouette — figure facing wall with shadow",
        "compass and ruler crossed — Masonic philosophy",
        "phoenix feather and dagger crossed — eternal questioning",
    ],
}


# =====================================================================================
# DECONFLICTION HELPERS
# Maps legacy fields (coverage, strength) onto the new intensity preset, so old
# clients still work while we migrate the wizard.
# =====================================================================================

def coalesce_intensity(intensity: Optional[str], coverage: Optional[str], strength: Optional[str]) -> str:
    """Translate any combination of legacy (coverage, strength) and new (intensity) into one preset."""
    if intensity:
        norm = intensity.strip().lower()
        if norm in INTENSITY_PRESETS:
            return norm

    cov = (coverage or "").strip().lower()
    stren = (strength or "").strip().lower()

    if cov == "small":
        if stren == "subtle":
            return "whisper"
        return "personal"
    if cov == "medium":
        if stren == "bold":
            return "commanding"
        return "personal"
    if cov == "large":
        if stren == "subtle":
            return "personal"
        if stren == "bold":
            return "centerpiece"
        return "commanding"

    if stren == "subtle":
        return "whisper"
    if stren == "bold":
        return "commanding"
    return "personal"


def pick_motif_for_style(style: str, rng: Random) -> str:
    """Pick one concrete motif from the style's library."""
    library = STYLE_MOTIFS.get(style, AUTO_FALLBACK_MOTIFS)
    return rng.choice(library)


def pick_motif_for_theme(theme: str, rng: Random, fallback: Optional[str] = None) -> str:
    """Pick one concrete motif for a meaning theme."""
    key = (theme or "").strip().lower()
    library = THEME_MOTIFS.get(key)
    if not library:
        if fallback and fallback in STYLE_MOTIFS:
            return rng.choice(STYLE_MOTIFS[fallback])
        return "a meaningful personal symbol that captures the chosen theme"
    return rng.choice(library)


def get_intensity(intensity: str) -> dict[str, str]:
    """Look up an intensity preset, defaulting to 'personal' if unknown."""
    return INTENSITY_PRESETS.get(intensity, INTENSITY_PRESETS["personal"])


def get_region_anatomy(region: str) -> str:
    """Look up the region anatomy block, defaulting to 'other'."""
    return REGION_ANATOMY.get(region, REGION_ANATOMY["other"])
