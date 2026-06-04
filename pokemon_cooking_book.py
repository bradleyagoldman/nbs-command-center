#!/usr/bin/env python3
"""
Pokémon Quest Cooking Book PDF Generator  v3
- Drawn ingredient icons (mushroom, honey jar, bone, shell, rainbow, etc.)
- Three recipe rows per card:
    ⭐ Best (with Rainbow Matter)
    🍳 No Rainbow Matter
    🌿 Common Only (no Rainbow Matter AND no Mystical Shell)
- Correct combo data from allRecipesDatabase.js
"""

import math
import re
import time
from pathlib import Path

import requests
from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfgen_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ASSETS_DIR = Path("assets")
ASSETS_DIR.mkdir(exist_ok=True)
(ASSETS_DIR / "pokemon").mkdir(exist_ok=True)
(ASSETS_DIR / "ingredients").mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (personal-use PDF builder)"}
BOLD_FONT    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Register DejaVu with ReportLab so it can render ★, ♀, ♂, é, etc.
pdfmetrics.registerFont(TTFont("DV-Bold",    BOLD_FONT))
pdfmetrics.registerFont(TTFont("DV-Regular", REGULAR_FONT))

# Ingredient: m_no → (label, slug)
INGREDIENTS = {
    1:  ("Tiny Mushroom",  "tinymushroom"),
    2:  ("Big Root",       "bigroot"),
    3:  ("Bluk Berry",     "blukberry"),
    4:  ("Icy Rock",       "icyrock"),
    5:  ("Apricorn",       "apricorn"),
    6:  ("Honey",          "honey"),
    7:  ("Fossil",         "fossil"),
    8:  ("Balm Mushroom",  "balmmushroom"),
    9:  ("Rainbow Matter", "rainbowmatter"),
    10: ("Mystical Shell", "mysticalshell"),
}

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
COLOR_TO_KEY = {"Red": "red", "Blue": "blue", "Yellow": "yellow", "Gray": "grey"}
RECIPE_IDX_TO_KEY = [
    "any","red","blue","yellow","grey","water","normal","poison","ground","grass",
    "bug","psychic","rock","flying","fire","electric","fighting","legendary",
]
LEGENDARY_DEX = {144, 145, 146, 150, 151}

OBTAINABLE = [
    (1,"Bulbasaur","Bulbasaur"),(4,"Charmander","Charmander"),(7,"Squirtle","Squirtle"),
    (10,"Caterpie","Caterpie"),(13,"Weedle","Weedle"),(16,"Pidgey","Pidgey"),
    (19,"Rattata","Rattata"),(21,"Spearow","Spearow"),(23,"Ekans","Ekans"),
    (25,"Pikachu","Pikachu"),(27,"Sandshrew","Sandshrew"),(29,"Nidoran ♀","Nidoran♀"),
    (32,"Nidoran ♂","Nidoran♂"),(35,"Clefairy","Clefairy"),(37,"Vulpix","Vulpix"),
    (39,"Jigglypuff","Jigglypuff"),(41,"Zubat","Zubat"),(43,"Oddish","Oddish"),
    (46,"Paras","Paras"),(48,"Venonat","Venonat"),(50,"Diglett","Diglett"),
    (52,"Meowth","Meowth"),(54,"Psyduck","Psyduck"),(56,"Mankey","Mankey"),
    (58,"Growlithe","Growlithe"),(60,"Poliwag","Poliwag"),(63,"Abra","Abra"),
    (66,"Machop","Machop"),(69,"Bellsprout","Bellsprout"),(72,"Tentacool","Tentacool"),
    (74,"Geodude","Geodude"),(77,"Ponyta","Ponyta"),(79,"Slowpoke","Slowpoke"),
    (81,"Magnemite","Magnemite"),(83,"Farfetch'd","Farfetch'd"),(84,"Doduo","Doduo"),
    (86,"Seel","Seel"),(88,"Grimer","Grimer"),(90,"Shellder","Shellder"),
    (92,"Gastly","Gastly"),(95,"Onix","Onix"),(96,"Drowzee","Drowzee"),
    (98,"Krabby","Krabby"),(100,"Voltorb","Voltorb"),(102,"Exeggcute","Exeggcute"),
    (104,"Cubone","Cubone"),(106,"Hitmonlee","Hitmonlee"),(107,"Hitmonchan","Hitmonchan"),
    (108,"Lickitung","Lickitung"),(109,"Koffing","Koffing"),(111,"Rhyhorn","Rhyhorn"),
    (113,"Chansey","Chansey"),(114,"Tangela","Tangela"),(115,"Kangaskhan","Kangaskhan"),
    (116,"Horsea","Horsea"),(118,"Goldeen","Goldeen"),(120,"Staryu","Staryu"),
    (122,"Mr. Mime","MrMime"),(123,"Scyther","Scyther"),(124,"Jynx","Jynx"),
    (125,"Electabuzz","Electabuzz"),(126,"Magmar","Magmar"),(127,"Pinsir","Pinsir"),
    (128,"Tauros","Tauros"),(129,"Magikarp","Magikarp"),(131,"Lapras","Lapras"),
    (132,"Ditto","Ditto"),(133,"Eevee","Eevee"),(137,"Porygon","Porygon"),
    (138,"Omanyte","Omanyte"),(140,"Kabuto","Kabuto"),(142,"Aerodactyl","Aerodactyl"),
    (143,"Snorlax","Snorlax"),(144,"Articuno","Articuno"),(145,"Zapdos","Zapdos"),
    (146,"Moltres","Moltres"),(147,"Dratini","Dratini"),(150,"Mewtwo","Mewtwo"),
    (151,"Mew","Mew"),
]

BANNER_COLORS = [
    "#FF6B6B","#4ECDC4","#45B7D1","#96CEB4","#F7DC6F","#DDA0DD","#98D8C8",
    "#FFB347","#87CEEB","#F08080","#90EE90","#FFD700","#DA70D6","#20B2AA",
    "#FF8C00","#9B59B6","#3498DB","#E74C3C","#2ECC71","#F39C12",
]

session = requests.Session()
session.headers.update(HEADERS)

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def fetch(url, delay=0.4):
    try:
        time.sleep(delay)
        r = session.get(url, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  WARN {url}: {e}")
        return None

def hex_rgb(h):
    h = h.lstrip("#")
    return int(h[:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255

def fnt(size):
    try:
        return ImageFont.truetype(BOLD_FONT, size)
    except Exception:
        return ImageFont.load_default()

# ---------------------------------------------------------------------------
# Ingredient icon drawing  (150×150 RGBA PNG)
# ---------------------------------------------------------------------------

SZ = 150   # icon pixel size

def _base(bg=(252, 252, 255)):
    """White circle background with soft shadow."""
    img = PILImage.new("RGBA", (SZ, SZ), (0,0,0,0))
    d = ImageDraw.Draw(img)
    off = 6
    d.ellipse([off, off, SZ-1, SZ-1], fill=(0,0,0,35))         # shadow
    d.ellipse([0, 0, SZ-off-1, SZ-off-1], fill=bg,              # main circle
              outline=(200,200,210), width=2)
    return img, d

def icon_tiny_mushroom():
    img, d = _base()
    s = SZ - 6   # usable area inside circle
    cx = SZ // 2
    # Stem
    sw, sh = int(s*0.22), int(s*0.32)
    d.rounded_rectangle([cx-sw//2, int(SZ*0.60), cx+sw//2, int(SZ*0.88)],
                        radius=int(sw*0.35), fill=(235,215,185))
    # Cap (red)
    d.ellipse([int(SZ*0.12), int(SZ*0.14), int(SZ*0.88), int(SZ*0.66)],
              fill=(220,50,40))
    # Cap underside curve
    d.arc([int(SZ*0.12), int(SZ*0.48), int(SZ*0.88), int(SZ*0.72)],
          start=0, end=180, fill=(240,220,195), width=5)
    # White polka dots
    dots = [(0.36,0.30),(0.62,0.24),(0.51,0.46)]
    dr = int(SZ*0.075)
    for bx,by in dots:
        d.ellipse([int(bx*SZ)-dr, int(by*SZ)-dr, int(bx*SZ)+dr, int(by*SZ)+dr],
                  fill=(255,255,255,210))
    return img

def icon_big_root():
    img, d = _base((255,252,248))
    cx = SZ // 2
    # Leafy top (3 green teardrop leaves)
    for angle, ox, oy in [(-20, -12, -8), (0, 0, -14), (20, 12, -8)]:
        pts = []
        for t in range(0, 360, 10):
            r = math.radians(t)
            x = math.cos(r)*14 + ox + cx
            y = math.sin(r)*22 + oy + 28
            pts.append((x, y))
        d.polygon(pts, fill=(80, 160, 60))
        # vein
        d.line([(ox+cx, oy+16), (ox+cx, oy+44)], fill=(50,120,40), width=2)
    # Orange root body (tapered oval)
    d.ellipse([int(SZ*0.28), int(SZ*0.32), int(SZ*0.72), int(SZ*0.78)],
              fill=(230,110,30))
    # Side bumps (rootlets)
    bump_col = (200,80,20)
    d.ellipse([int(SZ*0.10), int(SZ*0.50), int(SZ*0.32), int(SZ*0.66)], fill=bump_col)
    d.ellipse([int(SZ*0.68), int(SZ*0.48), int(SZ*0.90), int(SZ*0.65)], fill=bump_col)
    # Root tip
    pts = [(cx-8, int(SZ*0.76)), (cx+8, int(SZ*0.76)), (cx, int(SZ*0.90))]
    d.polygon(pts, fill=(190,70,15))
    # Highlight stripe
    d.ellipse([int(SZ*0.36), int(SZ*0.36), int(SZ*0.52), int(SZ*0.54)],
              fill=(250,155,80))
    return img

def icon_bluk_berry():
    img, d = _base((248,248,255))
    # 3 dark blue berries in a triangle
    berry_col = (60,50,160)
    shine_col = (120,110,220)
    positions = [(int(SZ*0.38), int(SZ*0.52)), (int(SZ*0.62), int(SZ*0.52)),
                 (int(SZ*0.50), int(SZ*0.34))]
    br = int(SZ*0.17)
    for bx, by in positions:
        d.ellipse([bx-br, by-br, bx+br, by+br], fill=berry_col)
        # Shine
        sr = int(br*0.35)
        d.ellipse([bx-br//3-sr, by-br//2-sr, bx-br//3+sr, by-br//2+sr],
                  fill=shine_col)
    # Green leaf at top
    leaf = [(int(SZ*0.50), int(SZ*0.20)), (int(SZ*0.38), int(SZ*0.30)),
            (int(SZ*0.50), int(SZ*0.28)), (int(SZ*0.62), int(SZ*0.30))]
    d.polygon(leaf, fill=(60,150,50))
    # Stem
    d.line([(int(SZ*0.50), int(SZ*0.20)), (int(SZ*0.50), int(SZ*0.30))],
           fill=(80,60,30), width=3)
    return img

def icon_icy_rock():
    img, d = _base((240,248,255))
    cx, cy = SZ//2, SZ//2
    # Main crystal shape (hexagon rotated)
    pts = []
    for i in range(6):
        angle = math.radians(i*60 + 30)
        pts.append((cx + int(math.cos(angle)*SZ*0.36),
                    cy + int(math.sin(angle)*SZ*0.36)))
    d.polygon(pts, fill=(130,200,240))
    # Inner facet
    pts2 = []
    for i in range(6):
        angle = math.radians(i*60 + 30)
        pts2.append((cx + int(math.cos(angle)*SZ*0.22),
                     cy + int(math.sin(angle)*SZ*0.22)))
    d.polygon(pts2, fill=(180,225,255))
    # Edge lines
    for i in range(6):
        a1 = math.radians(i*60 + 30)
        a2 = math.radians((i+1)*60 + 30)
        d.line([(cx + int(math.cos(a1)*SZ*0.36), cy + int(math.sin(a1)*SZ*0.36)),
                (cx, cy)], fill=(100,170,220), width=1)
    # Sparkle stars
    def sparkle(sx, sy, r):
        for angle in [0, 90, 180, 270]:
            a = math.radians(angle)
            d.line([(sx, sy), (sx+int(math.cos(a)*r), sy+int(math.sin(a)*r))],
                   fill=(255,255,255), width=2)
    sparkle(int(SZ*0.70), int(SZ*0.22), 8)
    sparkle(int(SZ*0.25), int(SZ*0.72), 6)
    return img

def icon_apricorn():
    img, d = _base((255,255,240))
    cx = SZ//2
    # Body (yellow sphere)
    d.ellipse([int(SZ*0.18), int(SZ*0.24), int(SZ*0.82), int(SZ*0.86)],
              fill=(240,210,30))
    # Highlight
    d.ellipse([int(SZ*0.28), int(SZ*0.30), int(SZ*0.48), int(SZ*0.48)],
              fill=(255,245,120))
    # Brown acorn cap
    d.ellipse([int(SZ*0.22), int(SZ*0.20), int(SZ*0.78), int(SZ*0.44)],
              fill=(130,80,30))
    # Cap texture lines
    for i in range(4):
        x = int(SZ*0.26) + i*16
        d.arc([x, int(SZ*0.22), x+14, int(SZ*0.42)], start=180, end=0,
              fill=(100,55,15), width=2)
    # Stem
    d.rounded_rectangle([cx-4, int(SZ*0.12), cx+4, int(SZ*0.24)],
                        radius=3, fill=(90,50,10))
    # Green leaf
    pts = [(cx, int(SZ*0.14)), (cx-14, int(SZ*0.08)), (cx+10, int(SZ*0.07))]
    d.polygon(pts, fill=(60,140,40))
    return img

def icon_honey():
    img, d = _base((255,252,230))
    cx, cy = SZ//2, SZ//2
    # Hexagon body
    pts = []
    for i in range(6):
        angle = math.radians(i*60)
        pts.append((cx + int(math.cos(angle)*SZ*0.33),
                    cy + int(math.sin(angle)*SZ*0.33)))
    d.polygon(pts, fill=(250,180,20))
    # Hexagon outline
    d.polygon(pts, fill=None, outline=(200,130,0), width=3)
    # Inner honeycomb cells (3 mini hexagons)
    for sx, sy, sc in [(cx, cy, 0.12), (cx-16, cy-9, 0.08), (cx+16, cy-9, 0.08)]:
        mini = []
        for i in range(6):
            a = math.radians(i*60)
            mini.append((sx + int(math.cos(a)*SZ*sc),
                         sy + int(math.sin(a)*SZ*sc)))
        d.polygon(mini, fill=None, outline=(200,130,0), width=2)
    # Honey drip at bottom
    drip_pts = [(cx-10, int(SZ*0.72)), (cx+10, int(SZ*0.72)),
                (cx+6, int(SZ*0.86)), (cx, int(SZ*0.90)), (cx-6, int(SZ*0.86))]
    d.polygon(drip_pts, fill=(230,160,10))
    # Shine
    d.ellipse([int(SZ*0.38), int(SZ*0.32), int(SZ*0.50), int(SZ*0.44)],
              fill=(255,240,120))
    return img

def icon_fossil():
    img, d = _base((245,245,245))
    # Classic bone shape: bar + round ends
    bone_col = (180,175,165)
    dark_col = (140,130,120)
    bar_y = int(SZ*0.44)
    bar_h = int(SZ*0.16)
    bar_x1, bar_x2 = int(SZ*0.22), int(SZ*0.78)
    # Bar
    d.rectangle([bar_x1, bar_y, bar_x2, bar_y+bar_h], fill=bone_col)
    # Left knob circles
    lr = int(SZ*0.14)
    d.ellipse([bar_x1-lr, bar_y-lr//2, bar_x1+lr, bar_y+bar_h+lr//2], fill=bone_col)
    d.ellipse([bar_x1-lr+4, bar_y-lr//2+4, bar_x1+lr-4, bar_y+bar_h+lr//2-4],
              fill=(210,205,198))
    # Right knob circles
    d.ellipse([bar_x2-lr, bar_y-lr//2, bar_x2+lr, bar_y+bar_h+lr//2], fill=bone_col)
    d.ellipse([bar_x2-lr+4, bar_y-lr//2+4, bar_x2+lr-4, bar_y+bar_h+lr//2-4],
              fill=(210,205,198))
    # Fossil crack marks
    cx = SZ//2
    d.line([(cx-5, bar_y-4), (cx+2, bar_y+bar_h+4)], fill=dark_col, width=2)
    d.line([(cx+8, bar_y-3), (cx+15, bar_y+bar_h+2)], fill=dark_col, width=1)
    return img

def icon_balm_mushroom():
    """Larger drooping gray mushroom, clearly different from Tiny Mushroom."""
    img, d = _base((248,248,252))
    cx = SZ//2
    # Thick stem (gray)
    sw = int(SZ*0.24)
    d.rounded_rectangle([cx-sw//2, int(SZ*0.50), cx+sw//2, int(SZ*0.88)],
                        radius=int(sw*0.3), fill=(175,185,190))
    # Gills under cap
    d.arc([int(SZ*0.14), int(SZ*0.42), int(SZ*0.86), int(SZ*0.68)],
          start=0, end=180, fill=(155,165,175), width=6)
    # Wide drooping cap (dark gray)
    d.ellipse([int(SZ*0.08), int(SZ*0.10), int(SZ*0.92), int(SZ*0.58)],
              fill=(100,115,125))
    # Wavy/drooping cap edge
    for i in range(6):
        x = int(SZ*0.10) + i*int(SZ*0.14)
        d.arc([x, int(SZ*0.42), x+int(SZ*0.18), int(SZ*0.62)],
              start=180, end=360, fill=(80,95,105), width=4)
    # Cap highlight (lighter stripe)
    d.arc([int(SZ*0.20), int(SZ*0.14), int(SZ*0.64), int(SZ*0.36)],
          start=210, end=300, fill=(150,165,175), width=5)
    return img

def icon_rainbow_matter():
    img, d = _base((250,245,255))
    cx, cy = SZ//2, int(SZ*0.62)
    rainbow_colors = [
        (255,60,60), (255,155,30), (255,230,0),
        (50,200,50), (50,140,240), (80,60,220), (190,60,210)
    ]
    # Draw concentric arcs (rainbow)
    for i, col in enumerate(rainbow_colors):
        outer_r = int(SZ*0.40) - i*6
        if outer_r < 8:
            break
        d.arc([cx-outer_r, cy-outer_r, cx+outer_r, cy+outer_r],
              start=180, end=360, fill=col, width=6)
    # Sparkle stars
    def star(sx, sy, r, col=(255,255,255)):
        for angle in [0, 45, 90, 135]:
            a = math.radians(angle)
            d.line([(int(sx-math.cos(a)*r), int(sy-math.sin(a)*r)),
                    (int(sx+math.cos(a)*r), int(sy+math.sin(a)*r))],
                   fill=col, width=2)
    star(int(SZ*0.20), int(SZ*0.22), 7, (255,220,0))
    star(int(SZ*0.78), int(SZ*0.18), 9, (255,180,255))
    star(int(SZ*0.65), int(SZ*0.72), 6, (180,220,255))
    # Small cloud/base
    d.ellipse([int(SZ*0.28), int(SZ*0.60), int(SZ*0.72), int(SZ*0.80)],
              fill=(255,255,255))
    return img

def icon_mystical_shell():
    """Gold nautilus-style shell."""
    img, d = _base((255,252,235))
    cx, cy = SZ//2, int(SZ*0.52)
    # Outer shell body
    d.ellipse([int(SZ*0.14), int(SZ*0.16), int(SZ*0.86), int(SZ*0.84)],
              fill=(210,165,40))
    # Inner spiral zones (darker gold → lighter center)
    zones = [
        (int(SZ*0.22), int(SZ*0.24), int(SZ*0.78), int(SZ*0.76), (190,140,25)),
        (int(SZ*0.30), int(SZ*0.32), int(SZ*0.70), int(SZ*0.68), (230,185,60)),
        (int(SZ*0.38), int(SZ*0.40), int(SZ*0.62), int(SZ*0.60), (245,215,100)),
        (int(SZ*0.44), int(SZ*0.46), int(SZ*0.56), int(SZ*0.56), (255,240,160)),
    ]
    for x1,y1,x2,y2,col in zones:
        d.ellipse([x1,y1,x2,y2], fill=col)
    # Spiral lines (emanating arcs)
    spiral_col = (170,120,15)
    for i, (start, end) in enumerate([(0,90),(90,180),(180,270),(270,360)]):
        r = int(SZ*0.30) + i*4
        d.arc([cx-r, cy-r, cx+r, cy+r], start=start, end=end,
              fill=spiral_col, width=2)
    # Flat edge (left side of nautilus)
    d.chord([int(SZ*0.14), int(SZ*0.16), int(SZ*0.40), int(SZ*0.84)],
            start=90, end=270, fill=(180,135,20))
    # Ridge lines on flat edge
    for yy in range(int(SZ*0.25), int(SZ*0.75), 10):
        d.line([(int(SZ*0.18), yy), (int(SZ*0.30), yy)],
               fill=(220,175,40), width=1)
    # Pearl highlight
    d.ellipse([int(SZ*0.55), int(SZ*0.28), int(SZ*0.72), int(SZ*0.42)],
              fill=(255,250,220))
    return img

ICON_FUNCS = {
    1: icon_tiny_mushroom,
    2: icon_big_root,
    3: icon_bluk_berry,
    4: icon_icy_rock,
    5: icon_apricorn,
    6: icon_honey,
    7: icon_fossil,
    8: icon_balm_mushroom,
    9: icon_rainbow_matter,
    10: icon_mystical_shell,
}

_INGREDIENT_IMG_BASE = (
    "https://raw.githubusercontent.com/gianemi2/"
    "pokemon-quest-recipes-maker/master/assets/ingredient-image"
)

def make_all_icons():
    """Download real game ingredient sprites; fall back to PIL drawing."""
    ready = 0
    for ing_id, (label, slug) in INGREDIENTS.items():
        dest = ASSETS_DIR / "ingredients" / f"{slug}.png"
        if dest.exists() and dest.stat().st_size > 500:
            ready += 1
            continue
        url = f"{_INGREDIENT_IMG_BASE}/{slug}.png"
        try:
            time.sleep(0.3)
            r = session.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 500:
                dest.write_bytes(r.content)
                ready += 1
                continue
        except Exception:
            pass
        # Fallback: PIL-drawn icon
        ICON_FUNCS[ing_id]().save(dest, "PNG")
        ready += 1
    print(f"  {ready} ingredient icons ready")

# ---------------------------------------------------------------------------
# Data parsing
# ---------------------------------------------------------------------------

def parse_poke_data(text):
    recipe_map, color_map = {}, {}
    names = list(re.finditer(r'name:\s+"([^"]+)"', text))
    for i, m in enumerate(names):
        name = m.group(1)
        start = m.end()
        end = names[i+1].start() if i+1 < len(names) else len(text)
        block = text[start:end]
        cm = re.search(r'color:\s+"([^"]+)"', block)
        if cm:
            color_map[name] = cm.group(1)
        specials = re.findall(r'([A-Za-z]+)_special:\s+"?([\d.]+)%?"', block)
        if specials:
            best_type = max(specials, key=lambda x: float(x[1]))[0]
            recipe_map[name] = POKE_TO_DB.get(best_type, "any")
    return recipe_map, color_map

def parse_recipe_db(text):
    it_start = text.find('"IT"')
    en_text = text[:it_start] if it_start > 0 else text
    best = {}
    m_no_matches = list(re.finditer(r'"m_no":\s*(\d+)', en_text))
    for i, m in enumerate(m_no_matches):
        idx = int(m.group(1))
        start = m.end()
        end = m_no_matches[i+1].start() if i+1 < len(m_no_matches) else len(en_text)
        section = en_text[start:end]
        pm = re.search(r'"pokemon":\s*\{(.*?)\}(?=\s*\})', section, re.DOTALL)
        if not pm:
            continue
        for lm in re.finditer(r'"(\d+)":\s*\[(.*?)\]', pm.group(1), re.DOTALL):
            level = int(lm.group(1))
            for poke in re.findall(r'"([^"]+)"', lm.group(2)):
                poke = poke.strip()
                curr = best.get(poke)
                if curr is None or level > curr[1] or (level == curr[1] and idx != 0 and curr[0] == 0):
                    best[poke] = (idx, level)
    return {name: RECIPE_IDX_TO_KEY[idx] for name,(idx,_) in best.items() if idx < len(RECIPE_IDX_TO_KEY)}

def parse_combos(text):
    """
    Returns {db_key: (best, rns, simple)}
    best   = best overall (may include Rainbow + Shell) — used for legendary row A
    rns    = best WITH Rainbow (9) but WITHOUT Shell (10) — used for non-legendary row A
    simple = best WITHOUT Rainbow OR Shell — used for row B (everyone)
    """
    result = {}
    key_pat = re.compile(
        r'"(any|red|blue|yellow|grey|water|normal|poison|ground|grass'
        r'|bug|psychic|rock|flying|fire|electric|fighting|legendary)"'
        r'\s*:\s*\{[^{]*"recipes"\s*:\s*\[', re.DOTALL
    )
    for km in key_pat.finditer(text):
        db_key = km.group(1)
        start = km.end()
        depth = 1; i = start
        while i < len(text) and depth > 0:
            if text[i] == '[': depth += 1
            elif text[i] == ']': depth -= 1
            i += 1
        array_text = text[start:i-1]

        best_p, best_c = -1.0, []
        rns_p,  rns_c  = -1.0, []   # rainbow, no shell
        simp_p, simp_c = -1.0, []   # no rainbow, no shell

        for em in re.finditer(r'\{[^{}]+\}', array_text, re.DOTALL):
            entry = em.group(0)
            pm = re.search(r'"m_itemPriceAverage":\s*([\d.]+)', entry)
            if not pm: continue
            price = float(pm.group(1))
            nos_m = re.search(r'"m_itemNo":\s*\[([\d,\s]+)\]', entry)
            cnt_m = re.search(r'"m_itemNoCount":\s*\[([\d,\s]+)\]', entry)
            if not nos_m or not cnt_m: continue
            nos = [int(x) for x in nos_m.group(1).split(',') if x.strip()]
            cnts = [int(x) for x in cnt_m.group(1).split(',') if x.strip()]
            combo = []
            for n,c in zip(nos,cnts): combo.extend([n]*c)
            if len(combo) != 5: continue
            if price > best_p:
                best_p, best_c = price, combo
            if 9 in combo and 10 not in combo and price > rns_p:
                rns_p, rns_c = price, combo
            if 9 not in combo and 10 not in combo and price > simp_p:
                simp_p, simp_c = price, combo

        if best_c:
            easy_no_shell = rns_c if rns_c else best_c
            simp = simp_c if simp_c else easy_no_shell
            result[db_key] = (best_c, easy_no_shell, simp)
    return result

# ---------------------------------------------------------------------------
# Image download
# ---------------------------------------------------------------------------

def download_pokemon_image(dex_num):
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
# PDF layout
# ---------------------------------------------------------------------------

PAGE_W, PAGE_H = A4   # 595 x 842 pt

def make_title_page(c):
    w, h = PAGE_W, PAGE_H
    c.setFillColorRGB(1.0, 0.99, 0.92)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColorRGB(1.0, 0.42, 0.42)
    c.rect(0, h*0.58, w, h*0.42, fill=1, stroke=0)
    for cx, cy, r, a in [(w*0.85,h*0.92,90,0.12),(w*0.10,h*0.66,55,0.10),(w*0.50,h*0.78,115,0.08)]:
        c.setFillColorRGB(1,1,1); c.setFillAlpha(a)
        c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillAlpha(1.0)
    c.setFillColorRGB(1,1,1)
    c.setFont("DV-Bold", 58); c.drawCentredString(w/2, h*0.845, "Pokémon")
    c.setFont("DV-Bold", 48); c.drawCentredString(w/2, h*0.745, "Cooking Book")
    c.setFillColorRGB(1.0,0.85,0.0)
    c.roundRect(w*0.10, h*0.615, w*0.80, 34, 17, fill=1, stroke=0)
    c.setFillColorRGB(0.2,0.10,0.0); c.setFont("DV-Bold", 17)
    c.drawCentredString(w/2, h*0.625, "Look, Cook and Count the Ingredients!")
    c.setFillColorRGB(0.30,0.80,0.78)
    c.rect(0, 0, w, h*0.37, fill=1, stroke=0)
    c.setFillColorRGB(0.20,0.65,0.63)
    c.roundRect(w*0.29, h*0.09, w*0.42, h*0.22, 28, fill=1, stroke=0)
    c.setFillColorRGB(1,1,1); c.setFont("DV-Bold",28)
    c.drawCentredString(w/2, h*0.175, "Time to Cook!")
    c.setFont("DV-Regular",14); c.drawCentredString(w/2, h*0.14, "79 Pokemon inside!")
    c.setFillColorRGB(1,1,1); c.setFillAlpha(0.45); c.setFont("DV-Regular", 9)
    c.drawCentredString(w/2, 14, "Pokemon Quest Cooking Book  *  Personal home use  *  79 Pokemon inside!")
    c.setFillAlpha(1.0)
    c.showPage()


def draw_ingredient_row(c, ing_ids, sx, row_y, card_w, card_h, gap, border_r, border_g, border_b):
    """Draw a row of 5 ingredient cards."""
    for idx, ing_id in enumerate(ing_ids):
        cx = sx + idx * (card_w + gap)
        name, slug = INGREDIENTS.get(ing_id, ("?","?"))

        # Card background
        c.setFillColorRGB(1,1,1)
        c.setStrokeColorRGB(border_r, border_g, border_b)
        c.setLineWidth(2)
        c.roundRect(cx, row_y, card_w, card_h, 9, fill=1, stroke=1)

        # Ingredient image
        ing_img = ASSETS_DIR / "ingredients" / f"{slug}.png"
        isize = card_h - 30
        ix = cx + (card_w - isize)/2
        iy = row_y + 22

        if ing_img.exists():
            try:
                c.drawImage(str(ing_img), ix, iy, width=isize, height=isize,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                c.setFillColorRGB(0.85,0.85,0.85)
                c.rect(ix, iy, isize, isize, fill=1, stroke=0)
        else:
            c.setFillColorRGB(0.85,0.85,0.85)
            c.rect(ix, iy, isize, isize, fill=1, stroke=0)

        # Name label
        c.setFillColorRGB(0.12,0.12,0.12); c.setFont("DV-Bold", 11)
        words = name.split()
        if len(words) <= 2:
            c.drawCentredString(cx + card_w/2, row_y + 14, name)
        else:
            mid = (len(words)+1)//2
            c.drawCentredString(cx + card_w/2, row_y + 22, " ".join(words[:mid]))
            c.drawCentredString(cx + card_w/2, row_y + 9, " ".join(words[mid:]))


def make_card(c, display_name, dex_num, recipe_name, row_a_ids, row_b_ids, is_legendary, img_path, color_idx):
    w, h = PAGE_W, PAGE_H
    hex_col = BANNER_COLORS[color_idx % len(BANNER_COLORS)]
    cr, cg, cb = hex_rgb(hex_col)

    # Background
    c.setFillColorRGB(0.97, 0.97, 0.97)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Banner (33%)
    banner_h = h * 0.33
    c.setFillColorRGB(cr, cg, cb)
    c.rect(0, h - banner_h, w, banner_h, fill=1, stroke=0)
    c.setFillColorRGB(1,1,1); c.setFillAlpha(0.10)
    c.circle(w*0.82, h-banner_h*0.35, 90, fill=1, stroke=0)
    c.circle(w*0.12, h-28, 50, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Pokémon name
    c.setFillColorRGB(1,1,1); c.setFont("DV-Bold", 36)
    c.drawCentredString(w/2, h-50, display_name)

    # Pokémon image
    img_size = 125
    img_x = w/2 - img_size/2
    img_y = h - banner_h + (banner_h - img_size)/2 - 14
    if img_path and Path(img_path).exists():
        try:
            c.drawImage(img_path, img_x, img_y, width=img_size, height=img_size,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # Recipe badge
    short = recipe_name if len(recipe_name) <= 26 else recipe_name[:24]+"…"
    bw = min(len(short)*11+38, w-56)
    bx = w/2 - bw/2
    c.setFillColorRGB(0,0,0); c.setFillAlpha(0.22)
    c.roundRect(bx, h-banner_h+14, bw, 30, 15, fill=1, stroke=0)
    c.setFillAlpha(1.0); c.setFillColorRGB(1,1,1); c.setFont("DV-Bold", 16)
    c.drawCentredString(w/2, h-banner_h+20, f"Cook a {short}!")

    # --- Layout for TWO ingredient rows ---
    card_w = 90
    card_h = 95
    gap = 13
    n = 5
    total_row_w = n*card_w + (n-1)*gap
    sx = (w - total_row_w)/2

    content_top = h - banner_h - 52

    # Row A
    label_a_y = content_top - 24
    row_a_y   = label_a_y - card_h - 4
    badge_a_y = row_a_y - 22
    sep_y     = badge_a_y - 10

    # Row B
    label_b_y = sep_y - 14
    row_b_y   = label_b_y - card_h - 4
    badge_b_y = row_b_y - 22

    # Row A label & content
    if is_legendary:
        label_a_text = "★  Legendary Recipe  (Mystical Shell)"
        label_a_col  = (0.72, 0.55, 0.00)   # gold
    else:
        label_a_text = "★  With Rainbow Matter"
        label_a_col  = (0.55, 0.10, 0.80)   # purple

    c.setFillColorRGB(*label_a_col)
    c.roundRect(sx-4, label_a_y-2, total_row_w+8, 24, 7, fill=1, stroke=0)
    c.setFillColorRGB(1,1,1); c.setFont("DV-Bold", 13)
    c.drawString(sx+8, label_a_y+3, label_a_text)

    draw_ingredient_row(c, row_a_ids, sx, row_a_y, card_w, card_h, gap, cr, cg, cb)

    for idx in range(n):
        bx2 = sx + idx*(card_w+gap) + card_w/2
        c.setFillColorRGB(cr,cg,cb); c.circle(bx2, badge_a_y+11, 11, fill=1, stroke=0)
        c.setFillColorRGB(1,1,1); c.setFont("DV-Bold", 12)
        c.drawCentredString(bx2, badge_a_y+6, str(idx+1))

    # Separator
    c.setStrokeColorRGB(0.75,0.75,0.75); c.setLineWidth(1.5)
    c.line(sx, sep_y, sx+total_row_w, sep_y)

    # Row B label & content
    c.setFillColorRGB(0.88, 0.44, 0.05)
    c.roundRect(sx-4, label_b_y-2, total_row_w+8, 24, 7, fill=1, stroke=0)
    c.setFillColorRGB(1,1,1); c.setFont("DV-Bold", 13)

    if is_legendary:
        # Legendary Pokémon have no common substitute — show a note instead
        c.drawString(sx+8, label_b_y+3, "●  Everyday Ingredients")
        note_y = (row_b_y + row_b_y + card_h) / 2
        c.setFillColorRGB(0.50, 0.50, 0.50); c.setFont("DV-Bold", 15)
        c.drawCentredString(w/2, note_y + 14, "This Legendary can only be cooked")
        c.drawCentredString(w/2, note_y - 6, "with 5 Mystical Shells.")
        c.drawCentredString(w/2, note_y - 26, "No everyday substitute exists!")
    else:
        c.drawString(sx+8, label_b_y+3, "●  Everyday Ingredients")
        draw_ingredient_row(c, row_b_ids, sx, row_b_y, card_w, card_h, gap, cr, cg, cb)
        for idx in range(n):
            bx2 = sx + idx*(card_w+gap) + card_w/2
            c.setFillColorRGB(cr,cg,cb); c.circle(bx2, badge_b_y+11, 11, fill=1, stroke=0)
            c.setFillColorRGB(1,1,1); c.setFont("DV-Bold", 12)
            c.drawCentredString(bx2, badge_b_y+6, str(idx+1))

    # Counting prompt
    prompt_y = badge_b_y - 24
    if not is_legendary and prompt_y > 20:
        c.setFillColorRGB(0.35,0.35,0.35); c.setFont("DV-Bold", 13)
        c.drawCentredString(w/2, prompt_y, "Count 5 ingredients in each row -- can you do it?  ★")

    # Footer
    c.setFillColorRGB(0.68,0.68,0.68); c.setFont("DV-Regular", 9)
    c.drawCentredString(w/2, 12, f"#{dex_num:03d}  •  Pokemon Quest Cooking Book")

    c.showPage()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("="*62)
    print("Pokémon Quest Cooking Book  v3  (three recipes + real icons)")
    print("="*62)

    print("\n[1/5] Fetching data …")
    poke_text = fetch("https://raw.githubusercontent.com/justingolden21/pquest/main/js/pokeData.js")
    recipe_text = fetch("https://raw.githubusercontent.com/gianemi2/pokemon-quest-recipes-maker/master/database/recipeDatabase.js", 0.5)
    all_text = fetch("https://raw.githubusercontent.com/gianemi2/pokemon-quest-recipes-maker/master/database/allRecipesDatabase.js", 0.5)
    if not all([poke_text, recipe_text, all_text]):
        print("ERROR: data fetch failed"); return

    print("[2/5] Parsing …")
    specific_recipe, color_map = parse_poke_data(poke_text)
    db_recipe = parse_recipe_db(recipe_text)
    combos = parse_combos(all_text)
    print(f"  Type recipes: {len(specific_recipe)}  DB recipes: {len(db_recipe)}  Combos: {len(combos)}/18")

    print("[3/5] Drawing ingredient icons …")
    make_all_icons()

    print("[4/5] Downloading Pokémon artwork …")
    pokemon_list = []
    for dex_num, display_name, poke_key in OBTAINABLE:
        # Best recipe key
        if dex_num in LEGENDARY_DEX:
            db_key = "legendary"
        else:
            db_key = specific_recipe.get(poke_key)
            if not db_key:
                for alt in [poke_key.replace(".","").replace("'","").replace(" ",""),
                            display_name, display_name.replace(".","")]:
                    db_key = specific_recipe.get(alt)
                    if db_key: break
            if not db_key:
                for alt in [poke_key, display_name]:
                    k = db_recipe.get(alt)
                    if k and k != "any":
                        db_key = k; break
            if not db_key:
                poke_color = color_map.get(poke_key) or color_map.get(display_name, "Yellow")
                db_key = COLOR_TO_KEY.get(poke_color, "yellow")

        recipe_name = RECIPE_NAMES.get(db_key, "Special Recipe")
        combo_data = combos.get(db_key)
        if combo_data:
            best_ids, rns_ids, simple_ids = combo_data
        else:
            best_ids = rns_ids = simple_ids = [6,6,8,8,1]

        is_legendary = dex_num in LEGENDARY_DEX
        # Row A: for legendary use full best (Mystical Shell allowed);
        #        for everyone else use Rainbow + no Shell combo
        row_a = best_ids if is_legendary else rns_ids
        # Row B: always no Rainbow and no Shell (common ingredients)
        #        for legendary this shows an alternative without special items
        row_b = simple_ids

        img_path = download_pokemon_image(dex_num)
        marker = "L" if is_legendary else ("R" if 9 in row_a else " ")
        print(f"  #{dex_num:3d} {display_name:15s} → {recipe_name:22s}  [{marker}]")

        pokemon_list.append({
            "dex_num": dex_num, "display_name": display_name,
            "recipe_name": recipe_name,
            "row_a": row_a, "row_b": row_b,
            "is_legendary": is_legendary,
            "img_path": str(img_path) if img_path else None,
        })

    print("\n[5/5] Building PDF …")
    c = pdfgen_canvas.Canvas("pokemon-cooking-book.pdf", pagesize=A4)
    c.setTitle("Pokemon Quest Cooking Book")
    make_title_page(c)
    for idx, p in enumerate(pokemon_list):
        make_card(c, p["display_name"], p["dex_num"], p["recipe_name"],
                  p["row_a"], p["row_b"], p["is_legendary"],
                  p["img_path"], idx)
    c.save()

    print("\n"+"="*62)
    print("DONE")
    print(f"  Pokémon: {len(pokemon_list)}/79")
    print(f"  Recipe variety: {len(set(p['recipe_name'] for p in pokemon_list))} different recipes")
    missing = [p["display_name"] for p in pokemon_list if not p["img_path"]]
    if missing: print(f"  Missing artwork: {missing}")
    print("  Output: pokemon-cooking-book.pdf")
    print("="*62)

if __name__ == "__main__":
    main()
