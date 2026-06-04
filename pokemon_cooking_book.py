#!/usr/bin/env python3
"""
Pokémon Quest Cooking Book PDF Generator
Data: community repos (GitHub raw, open-access)
Images: PokeAPI official artwork + PIL-generated ingredient icons
"""

import io
import re
import time
from pathlib import Path

import requests
from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfgen_canvas

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ASSETS_DIR = Path("assets")
ASSETS_DIR.mkdir(exist_ok=True)
(ASSETS_DIR / "pokemon").mkdir(exist_ok=True)
(ASSETS_DIR / "ingredients").mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (personal-use PDF builder)"}

# Ingredient: m_no → (label, slug, hex_color)
INGREDIENTS = {
    1:  ("Tiny Mushroom",  "tinymushroom",  "#E57373"),
    2:  ("Big Root",       "bigroot",       "#EF9A9A"),
    3:  ("Bluk Berry",     "blukberry",     "#64B5F6"),
    4:  ("Icy Rock",       "icyrock",       "#4FC3F7"),
    5:  ("Apricorn",       "apricorn",      "#FFF176"),
    6:  ("Honey",          "honey",         "#FFD54F"),
    7:  ("Fossil",         "fossil",        "#B0BEC5"),
    8:  ("Balm Mushroom",  "balmmushroom",  "#90A4AE"),
    9:  ("Rainbow Matter", "rainbowmatter", "#CE93D8"),
    10: ("Mystical Shell", "mysticalshell", "#FFD700"),
}

# Recipe key → short name for display
RECIPE_NAMES = {
    "any":       "Mulligan Stew",
    "red":       "Red Stew",
    "blue":      "Blue Soda",
    "yellow":    "Yellow Curry",
    "grey":      "Gray Porridge",
    "water":     "Mouth-Watering Dip",
    "normal":    "Plain Crepe",
    "poison":    "Sludge Soup",
    "ground":    "Mud Pie",
    "grass":     "Veggie Smoothie",
    "bug":       "Honey Nectar",
    "psychic":   "Brain Food",
    "rock":      "Stone Soup",
    "flying":    "Light-as-Air Casserole",
    "fire":      "Hot Pot",
    "electric":  "Watt a Risotto",
    "fighting":  "Get Swole Syrup",
    "legendary": "Ambrosia of Legends",
}

# pokeData.js recipe prefix → allRecipesDatabase key
POKE_TO_DB = {
    "Mulligan": "any",  "Red": "red",     "Blue": "blue",
    "Yellow": "yellow", "Gray": "grey",   "Water": "water",
    "Normal": "normal", "Poison": "poison","Ground": "ground",
    "Grass": "grass",   "Bug": "bug",     "Psychic": "psychic",
    "Rock": "rock",     "Flying": "flying","Fire": "fire",
    "Electric": "electric","Fighting": "fighting","Ambrosia": "legendary",
    "Ghost": "poison",  "Dragon": "legendary","Ice": "blue",
    "Fairy": "normal",  "Steel": "grey",  "Dark": "poison",
}

# Color (from pokeData.js) → fallback recipe key
COLOR_TO_KEY = {"Red": "red", "Blue": "blue", "Yellow": "yellow", "Gray": "grey"}

# Recipe index (recipeDatabase order) → allRecipesDatabase key
RECIPE_IDX_TO_KEY = [
    "any", "red", "blue", "yellow", "grey",
    "water", "normal", "poison", "ground", "grass",
    "bug", "psychic", "rock", "flying", "fire",
    "electric", "fighting", "legendary",
]

# The 79 obtainable base-form Pokémon: (dex#, display_name, pokeData_name)
OBTAINABLE = [
    (1,   "Bulbasaur",   "Bulbasaur"),
    (4,   "Charmander",  "Charmander"),
    (7,   "Squirtle",    "Squirtle"),
    (10,  "Caterpie",    "Caterpie"),
    (13,  "Weedle",      "Weedle"),
    (16,  "Pidgey",      "Pidgey"),
    (19,  "Rattata",     "Rattata"),
    (21,  "Spearow",     "Spearow"),
    (23,  "Ekans",       "Ekans"),
    (25,  "Pikachu",     "Pikachu"),
    (27,  "Sandshrew",   "Sandshrew"),
    (29,  "Nidoran ♀",   "Nidoran♀"),
    (32,  "Nidoran ♂",   "Nidoran♂"),
    (35,  "Clefairy",    "Clefairy"),
    (37,  "Vulpix",      "Vulpix"),
    (39,  "Jigglypuff",  "Jigglypuff"),
    (41,  "Zubat",       "Zubat"),
    (43,  "Oddish",      "Oddish"),
    (46,  "Paras",       "Paras"),
    (48,  "Venonat",     "Venonat"),
    (50,  "Diglett",     "Diglett"),
    (52,  "Meowth",      "Meowth"),
    (54,  "Psyduck",     "Psyduck"),
    (56,  "Mankey",      "Mankey"),
    (58,  "Growlithe",   "Growlithe"),
    (60,  "Poliwag",     "Poliwag"),
    (63,  "Abra",        "Abra"),
    (66,  "Machop",      "Machop"),
    (69,  "Bellsprout",  "Bellsprout"),
    (72,  "Tentacool",   "Tentacool"),
    (74,  "Geodude",     "Geodude"),
    (77,  "Ponyta",      "Ponyta"),
    (79,  "Slowpoke",    "Slowpoke"),
    (81,  "Magnemite",   "Magnemite"),
    (83,  "Farfetch'd",  "Farfetch'd"),
    (84,  "Doduo",       "Doduo"),
    (86,  "Seel",        "Seel"),
    (88,  "Grimer",      "Grimer"),
    (90,  "Shellder",    "Shellder"),
    (92,  "Gastly",      "Gastly"),
    (95,  "Onix",        "Onix"),
    (96,  "Drowzee",     "Drowzee"),
    (98,  "Krabby",      "Krabby"),
    (100, "Voltorb",     "Voltorb"),
    (102, "Exeggcute",   "Exeggcute"),
    (104, "Cubone",      "Cubone"),
    (106, "Hitmonlee",   "Hitmonlee"),
    (107, "Hitmonchan",  "Hitmonchan"),
    (108, "Lickitung",   "Lickitung"),
    (109, "Koffing",     "Koffing"),
    (111, "Rhyhorn",     "Rhyhorn"),
    (113, "Chansey",     "Chansey"),
    (114, "Tangela",     "Tangela"),
    (115, "Kangaskhan",  "Kangaskhan"),
    (116, "Horsea",      "Horsea"),
    (118, "Goldeen",     "Goldeen"),
    (120, "Staryu",      "Staryu"),
    (122, "Mr. Mime",    "MrMime"),
    (123, "Scyther",     "Scyther"),
    (124, "Jynx",        "Jynx"),
    (125, "Electabuzz",  "Electabuzz"),
    (126, "Magmar",      "Magmar"),
    (127, "Pinsir",      "Pinsir"),
    (128, "Tauros",      "Tauros"),
    (129, "Magikarp",    "Magikarp"),
    (131, "Lapras",      "Lapras"),
    (132, "Ditto",       "Ditto"),
    (133, "Eevee",       "Eevee"),
    (137, "Porygon",     "Porygon"),
    (138, "Omanyte",     "Omanyte"),
    (140, "Kabuto",      "Kabuto"),
    (142, "Aerodactyl",  "Aerodactyl"),
    (143, "Snorlax",     "Snorlax"),
    (144, "Articuno",    "Articuno"),
    (145, "Zapdos",      "Zapdos"),
    (146, "Moltres",     "Moltres"),
    (147, "Dratini",     "Dratini"),
    (150, "Mewtwo",      "Mewtwo"),
    (151, "Mew",         "Mew"),
]

LEGENDARY_DEX = {144, 145, 146, 150, 151}

# Banner colours (cycling)
BANNER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#F7DC6F",
    "#DDA0DD", "#98D8C8", "#FFB347", "#87CEEB", "#F08080",
    "#90EE90", "#FFD700", "#DA70D6", "#20B2AA", "#FF8C00",
    "#9B59B6", "#3498DB", "#E74C3C", "#2ECC71", "#F39C12",
]

session = requests.Session()
session.headers.update(HEADERS)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def fetch(url: str, delay: float = 0.4) -> str | None:
    try:
        time.sleep(delay)
        r = session.get(url, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  WARN fetch {url}: {e}")
        return None


def hex_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return int(h[:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


# ---------------------------------------------------------------------------
# Data parsing
# ---------------------------------------------------------------------------

def parse_poke_data(text: str) -> tuple[dict, dict]:
    """
    Returns:
      recipe_map: {pokedata_name: best_db_key}
      color_map:  {pokedata_name: 'Red'|'Blue'|'Yellow'|'Gray'}
    """
    recipe_map: dict[str, str] = {}
    color_map: dict[str, str] = {}

    names = list(re.finditer(r'name:\s+"([^"]+)"', text))
    for i, m in enumerate(names):
        name = m.group(1)
        start = m.end()
        end = names[i + 1].start() if i + 1 < len(names) else len(text)
        block = text[start:end]

        # Color
        cm = re.search(r'color:\s+"([^"]+)"', block)
        if cm:
            color_map[name] = cm.group(1)

        # Best recipe at Special quality
        specials = re.findall(r'([A-Za-z]+)_special:\s+"?([\d.]+)%?"', block)
        if specials:
            best_type = max(specials, key=lambda x: float(x[1]))[0]
            recipe_map[name] = POKE_TO_DB.get(best_type, "any")

    return recipe_map, color_map


def parse_recipe_db(text: str) -> dict[str, str]:
    """
    Build {pokemon_name: db_key} from recipeDatabase.js.
    Priority: higher quality level wins; non-Mulligan beats Mulligan at same level.
    """
    it_start = text.find('"IT"')
    en_text = text[:it_start] if it_start > 0 else text

    best: dict[str, tuple[int, int]] = {}  # {name: (recipe_idx, level)}

    m_no_matches = list(re.finditer(r'"m_no":\s*(\d+)', en_text))
    for i, m in enumerate(m_no_matches):
        idx = int(m.group(1))
        start = m.end()
        end = m_no_matches[i + 1].start() if i + 1 < len(m_no_matches) else len(en_text)
        section = en_text[start:end]

        pm = re.search(r'"pokemon":\s*\{(.*?)\}(?=\s*\})', section, re.DOTALL)
        if not pm:
            continue
        for lm in re.finditer(r'"(\d+)":\s*\[(.*?)\]', pm.group(1), re.DOTALL):
            level = int(lm.group(1))
            for poke in re.findall(r'"([^"]+)"', lm.group(2)):
                poke = poke.strip()
                curr = best.get(poke)
                if curr is None:
                    best[poke] = (idx, level)
                else:
                    cidx, clevel = curr
                    if level > clevel or (level == clevel and idx != 0 and cidx == 0):
                        best[poke] = (idx, level)

    result = {}
    for name, (idx, _) in best.items():
        if idx < len(RECIPE_IDX_TO_KEY):
            result[name] = RECIPE_IDX_TO_KEY[idx]
    return result


def parse_best_combos(text: str) -> dict[str, list[int]]:
    """
    For each recipe key, find the ingredient combo with highest m_itemPriceAverage.
    Returns {db_key: [ing_id x5]}
    """
    result: dict[str, list[int]] = {}
    key_pat = re.compile(
        r'"(any|red|blue|yellow|grey|water|normal|poison|ground|grass'
        r'|bug|psychic|rock|flying|fire|electric|fighting|legendary)"'
        r'\s*:\s*\{[^{]*"recipes"\s*:\s*\[',
        re.DOTALL,
    )
    for m in key_pat.finditer(text):
        db_key = m.group(1)
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
            i += 1
        array_text = text[start : i - 1]

        best_price = -1.0
        best_combo: list[int] = []
        for em in re.finditer(r'\{[^{}]+\}', array_text, re.DOTALL):
            entry = em.group(0)
            pm = re.search(r'"m_itemPriceAverage":\s*([\d.]+)', entry)
            if not pm or float(pm.group(1)) <= best_price:
                continue
            nos_m = re.search(r'"m_itemNo":\s*\[([\d,\s]+)\]', entry)
            cnt_m = re.search(r'"m_itemNoCount":\s*\[([\d,\s]+)\]', entry)
            if not nos_m or not cnt_m:
                continue
            nos = [int(x) for x in nos_m.group(1).split(',') if x.strip()]
            cnts = [int(x) for x in cnt_m.group(1).split(',') if x.strip()]
            combo = []
            for ing_id, cnt in zip(nos, cnts):
                combo.extend([ing_id] * cnt)
            if len(combo) != 5:
                continue
            best_price = float(pm.group(1))
            best_combo = combo
        if best_combo:
            result[db_key] = best_combo
    return result


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

ICON_ABBREVS = {
    1: "🍄", 2: "🌿", 3: "🫐", 4: "🧊", 5: "🟡",
    6: "🍯", 7: "🦴", 8: "🍄", 9: "🌈", 10: "⭐",
}

def make_ingredient_icon(ing_id: int, size: int = 120) -> Path:
    name, slug, color_hex = INGREDIENTS[ing_id]
    dest = ASSETS_DIR / "ingredients" / f"{slug}.png"
    if dest.exists() and dest.stat().st_size > 100:
        return dest

    r, g, b = (int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16))
    img = PILImage.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Shadow
    off = size // 14
    draw.ellipse([off, off, size - 1, size - 1], fill=(0, 0, 0, 55))
    # Main disc
    draw.ellipse(
        [0, 0, size - off - 1, size - off - 1],
        fill=(r, g, b, 255),
        outline=(max(r - 50, 0), max(g - 50, 0), max(b - 50, 0), 200),
        width=3,
    )
    # Highlight
    hl = size // 4
    draw.ellipse([hl // 2, hl // 2, hl // 2 + hl, hl // 2 + hl], fill=(255, 255, 255, 70))

    # Ingredient-specific letter
    letter = name.split()[0][0].upper()
    if name == "Balm Mushroom":
        letter = "B"
    elif name == "Big Root":
        letter = "R"
    elif name == "Tiny Mushroom":
        letter = "T"
    elif name == "Mystical Shell":
        letter = "★"
    elif name == "Rainbow Matter":
        letter = "★"

    try:
        fnt = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=size // 3
        )
    except Exception:
        fnt = ImageFont.load_default()

    draw.text(
        (size // 2 - off // 2, size // 2 - off // 2),
        letter, fill=(255, 255, 255, 220), font=fnt, anchor="mm",
    )
    img.save(dest, "PNG")
    return dest


def download_pokemon_image(dex_num: int) -> Path | None:
    dest = ASSETS_DIR / "pokemon" / f"{dex_num}.png"
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    for url in [
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{dex_num}.png",
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{dex_num}.png",
    ]:
        try:
            time.sleep(0.4)
            r = session.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 500:
                dest.write_bytes(r.content)
                return dest
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

PAGE_W, PAGE_H = A4


def make_title_page(c: pdfgen_canvas.Canvas):
    w, h = PAGE_W, PAGE_H

    # Background
    c.setFillColorRGB(1.0, 0.99, 0.92)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Top banner
    c.setFillColorRGB(1.0, 0.42, 0.42)
    c.rect(0, h * 0.58, w, h * 0.42, fill=1, stroke=0)

    # Decorative circles
    for cx, cy, r, alpha in [
        (w * 0.85, h * 0.92, 90, 0.12),
        (w * 0.10, h * 0.66, 55, 0.10),
        (w * 0.50, h * 0.78, 115, 0.08),
    ]:
        c.setFillColorRGB(1, 1, 1)
        c.setFillAlpha(alpha)
        c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Main title
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 58)
    c.drawCentredString(w / 2, h * 0.845, "Pokémon")
    c.setFont("Helvetica-Bold", 48)
    c.drawCentredString(w / 2, h * 0.745, "Cooking Book")

    # Subtitle pill
    c.setFillColorRGB(1.0, 0.85, 0.0)
    c.roundRect(w * 0.10, h * 0.615, w * 0.80, 34, 17, fill=1, stroke=0)
    c.setFillColorRGB(0.2, 0.10, 0.0)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(w / 2, h * 0.625, "Look and Count the Ingredients!")

    # Lower band
    c.setFillColorRGB(0.30, 0.80, 0.78)
    c.rect(0, 0, w, h * 0.37, fill=1, stroke=0)

    # Pot graphic
    c.setFillColorRGB(0.20, 0.65, 0.63)
    c.roundRect(w * 0.29, h * 0.09, w * 0.42, h * 0.22, 28, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 64)
    c.drawCentredString(w / 2, h * 0.18, "🍲")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h * 0.075, "Time to Cook!")

    # Footer
    c.setFillColorRGB(1, 1, 1)
    c.setFillAlpha(0.45)
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, 14, "Pokémon Quest Cooking Book  •  For personal home use  •  79 Pokémon inside!")
    c.setFillAlpha(1.0)

    c.showPage()


def make_card(
    c: pdfgen_canvas.Canvas,
    display_name: str,
    dex_num: int,
    recipe_name: str,
    ingredient_ids: list[int],
    img_path: str | None,
    color_idx: int,
):
    w, h = PAGE_W, PAGE_H
    hex_col = BANNER_COLORS[color_idx % len(BANNER_COLORS)]
    cr, cg, cb = hex_rgb(hex_col)

    # Background
    c.setFillColorRGB(0.975, 0.975, 0.975)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Banner
    banner_h = h * 0.41
    c.setFillColorRGB(cr, cg, cb)
    c.rect(0, h - banner_h, w, banner_h, fill=1, stroke=0)

    # Circles
    c.setFillColorRGB(1, 1, 1)
    c.setFillAlpha(0.10)
    c.circle(w * 0.82, h - banner_h * 0.38, 90, fill=1, stroke=0)
    c.circle(w * 0.12, h - 28, 50, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Pokémon name
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 38)
    c.drawCentredString(w / 2, h - 58, display_name)

    # Pokémon image
    img_size = 145
    img_x = w / 2 - img_size / 2
    img_y = h - banner_h + (banner_h - img_size) / 2 - 16

    if img_path and Path(img_path).exists():
        try:
            c.drawImage(
                img_path, img_x, img_y,
                width=img_size, height=img_size,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:
            pass

    # Recipe badge
    short = recipe_name if len(recipe_name) <= 26 else recipe_name[:24] + "…"
    bw = min(len(short) * 13 + 44, w - 56)
    bx = w / 2 - bw / 2
    c.setFillColorRGB(0, 0, 0)
    c.setFillAlpha(0.22)
    c.roundRect(bx, h - banner_h + 18, bw, 32, 16, fill=1, stroke=0)
    c.setFillAlpha(1.0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - banner_h + 26, f"Cook a {short}!")

    # "Ingredients:" label
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(w / 2, h - banner_h - 42, "Ingredients:")

    # Ingredient cards
    n = len(ingredient_ids)
    if n == 0:
        c.showPage()
        return

    cw = 94
    ch = 122
    gap = 11
    total = n * cw + (n - 1) * gap
    sx = (w - total) / 2
    ry = h - banner_h - 56 - ch

    for idx, ing_id in enumerate(ingredient_ids):
        cx = sx + idx * (cw + gap)
        name, slug, hex_c = INGREDIENTS.get(ing_id, ("?", "?", "#CCCCCC"))
        ir, ig, ib = hex_rgb(hex_c)

        # Card
        c.setFillColorRGB(1, 1, 1)
        c.setStrokeColorRGB(cr, cg, cb)
        c.setLineWidth(2)
        c.roundRect(cx, ry, cw, ch, 10, fill=1, stroke=1)

        # Ingredient image
        ing_img = ASSETS_DIR / "ingredients" / f"{slug}.png"
        isize = 68
        ix = cx + (cw - isize) / 2
        iy = ry + 42

        if ing_img.exists():
            try:
                c.drawImage(
                    str(ing_img), ix, iy,
                    width=isize, height=isize,
                    preserveAspectRatio=True, mask="auto",
                )
            except Exception:
                _colored_circle(c, cx + cw / 2, iy + isize / 2, 28, ir, ig, ib)
        else:
            _colored_circle(c, cx + cw / 2, iy + isize / 2, 28, ir, ig, ib)

        # Label (up to 2 lines)
        c.setFillColorRGB(0.12, 0.12, 0.12)
        c.setFont("Helvetica-Bold", 12)
        words = name.split()
        if len(words) <= 2:
            c.drawCentredString(cx + cw / 2, ry + 15, name)
        else:
            mid = (len(words) + 1) // 2
            c.drawCentredString(cx + cw / 2, ry + 26, " ".join(words[:mid]))
            c.drawCentredString(cx + cw / 2, ry + 11, " ".join(words[mid:]))

    # Numbered badges above cards
    for idx in range(n):
        bx2 = sx + idx * (cw + gap) + cw / 2
        by2 = ry + ch + 8
        c.setFillColorRGB(cr, cg, cb)
        c.circle(bx2, by2 + 11, 13, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(bx2, by2 + 6, str(idx + 1))

    # Fun prompt
    c.setFillColorRGB(0.35, 0.35, 0.35)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, ry - 26, f"Count all {n} ingredients — can you do it?")

    # Footer
    c.setFillColorRGB(0.70, 0.70, 0.70)
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, 12, f"#{dex_num:03d}  •  Pokémon Quest Cooking Book")

    c.showPage()


def _colored_circle(c, cx, cy, r, cr, cg, cb):
    c.setFillColorRGB(cr, cg, cb)
    c.circle(cx, cy, r, fill=1, stroke=0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Pokémon Quest Cooking Book Generator")
    print("=" * 60)

    # ---- Fetch raw data ----
    print("\n[1/5] Fetching pokeData.js …")
    poke_text = fetch(
        "https://raw.githubusercontent.com/justingolden21/pquest/main/js/pokeData.js"
    )

    print("[2/5] Fetching recipeDatabase.js …")
    recipe_text = fetch(
        "https://raw.githubusercontent.com/gianemi2/pokemon-quest-recipes-maker/master/database/recipeDatabase.js",
        delay=0.5,
    )

    print("[3/5] Fetching allRecipesDatabase.js …")
    all_recipes_text = fetch(
        "https://raw.githubusercontent.com/gianemi2/pokemon-quest-recipes-maker/master/database/allRecipesDatabase.js",
        delay=0.5,
    )

    if not all([poke_text, recipe_text, all_recipes_text]):
        print("ERROR: One or more data sources unavailable. Aborting.")
        return

    # ---- Parse ----
    print("[4/5] Parsing data …")
    specific_recipe, color_map = parse_poke_data(poke_text)
    db_recipe = parse_recipe_db(recipe_text)
    best_combos = parse_best_combos(all_recipes_text)

    print(f"  Specific recipes (type-based): {len(specific_recipe)}")
    print(f"  Recipe DB mappings:            {len(db_recipe)}")
    print(f"  Ingredient combos:             {len(best_combos)} / 18")

    # ---- Ingredient icons ----
    print("[4b/5] Generating ingredient icons …")
    for ing_id in INGREDIENTS:
        make_ingredient_icon(ing_id)

    # ---- Pokémon cards ----
    print("[5/5] Downloading artwork & building card data …")
    pokemon_list = []
    failures = []

    for dex_num, display_name, poke_key in OBTAINABLE:
        # --- Determine best recipe ---
        if dex_num in LEGENDARY_DEX:
            db_key = "legendary"
        else:
            # 1. Type-specific from pokeData.js
            db_key = specific_recipe.get(poke_key)
            if not db_key:
                # Try name variations (Mr. Mime, Farfetch'd)
                for alt in [poke_key.replace(".", "").replace("'", "").replace(" ", ""),
                            display_name, display_name.replace(".", "")]:
                    db_key = specific_recipe.get(alt)
                    if db_key:
                        break

            if not db_key:
                # 2. recipeDatabase reverse-lookup (level-10 preference, non-Mulligan)
                for alt in [poke_key, display_name, poke_key.replace("♀", "♀").replace("♂", "♂")]:
                    db_key = db_recipe.get(alt)
                    if db_key and db_key != "any":
                        break

            if not db_key or db_key == "any":
                # 3. Color-based fallback
                poke_color = color_map.get(poke_key) or color_map.get(display_name, "Yellow")
                db_key = COLOR_TO_KEY.get(poke_color, "yellow")

        recipe_name = RECIPE_NAMES[db_key]
        ingredient_ids = best_combos.get(db_key, [8, 8, 9, 9, 10])

        # --- Download artwork ---
        img_path = download_pokemon_image(dex_num)
        if not img_path:
            failures.append(display_name)

        pokemon_list.append({
            "dex_num": dex_num,
            "display_name": display_name,
            "recipe_name": recipe_name,
            "ingredient_ids": ingredient_ids,
            "img_path": str(img_path) if img_path else None,
        })

        status = "✓" if img_path else "✗"
        print(f"  {status} #{dex_num:3d} {display_name:15s} → {recipe_name}")

    # ---- Build PDF ----
    print("\nBuilding PDF …")
    c = pdfgen_canvas.Canvas("pokemon-cooking-book.pdf", pagesize=A4)
    c.setTitle("Pokémon Quest Cooking Book")

    make_title_page(c)
    for idx, poke in enumerate(pokemon_list):
        make_card(
            c,
            display_name=poke["display_name"],
            dex_num=poke["dex_num"],
            recipe_name=poke["recipe_name"],
            ingredient_ids=poke["ingredient_ids"],
            img_path=poke["img_path"],
            color_idx=idx,
        )

    c.save()

    # ---- Summary ----
    recipe_variety = len(set(p["recipe_name"] for p in pokemon_list))
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Pokémon captured  : {len(pokemon_list)} / {len(OBTAINABLE)}")
    print(f"  Recipe variety    : {recipe_variety} different recipes")
    print(f"  Artwork missing   : {len(failures)}")
    if failures:
        print(f"  Missing           : {', '.join(failures)}")
    print("  Output            : pokemon-cooking-book.pdf")
    print("=" * 60)


if __name__ == "__main__":
    main()
