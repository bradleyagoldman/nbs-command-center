#!/usr/bin/env python3
"""
Generates the Pokémon Quest Cooking Book web app.
Output: web/index.html   web/manifest.json
"""

import json
import re
import time
from pathlib import Path
import requests

# ---------------------------------------------------------------------------
# Constants (mirrors pokemon_cooking_book.py)
# ---------------------------------------------------------------------------

HEADERS = {"User-Agent": "Mozilla/5.0 (personal-use web builder)"}

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
    "any": "Mulligan Stew", "red": "Red Stew", "blue": "Blue Soda",
    "yellow": "Yellow Curry", "grey": "Gray Porridge", "water": "Mouth-Watering Dip",
    "normal": "Plain Crepe", "poison": "Sludge Soup", "ground": "Mud Pie",
    "grass": "Veggie Smoothie", "bug": "Honey Nectar", "psychic": "Brain Food",
    "rock": "Stone Soup", "flying": "Light-as-Air Casserole", "fire": "Hot Pot",
    "electric": "Watt a Risotto", "fighting": "Get Swole Syrup",
    "legendary": "Ambrosia of Legends",
}

POKE_TO_DB = {
    "Mulligan": "any", "Red": "red", "Blue": "blue", "Yellow": "yellow",
    "Gray": "grey", "Water": "water", "Normal": "normal", "Poison": "poison",
    "Ground": "ground", "Grass": "grass", "Bug": "bug", "Psychic": "psychic",
    "Rock": "rock", "Flying": "flying", "Fire": "fire", "Electric": "electric",
    "Fighting": "fighting", "Ambrosia": "legendary",
    "Ghost": "poison", "Dragon": "legendary", "Ice": "blue",
    "Fairy": "normal", "Steel": "grey", "Dark": "poison",
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
    (81,"Magnemite","Magnemite"),(83,"Farfetch’d","Farfetch'd"),(84,"Doduo","Doduo"),
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

# ---------------------------------------------------------------------------
# Data fetching & parsing (same logic as pokemon_cooking_book.py)
# ---------------------------------------------------------------------------

session = requests.Session()
session.headers.update(HEADERS)

def fetch(url, delay=0.4):
    try:
        time.sleep(delay)
        r = session.get(url, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  WARN {url}: {e}")
        return None

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
        rns_p, rns_c = -1.0, []
        simp_p, simp_c = -1.0, []
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
            for n, c in zip(nos, cnts): combo.extend([n]*c)
            if len(combo) != 5: continue
            if price > best_p: best_p, best_c = price, combo
            if 9 in combo and 10 not in combo and price > rns_p: rns_p, rns_c = price, combo
            if 9 not in combo and 10 not in combo and price > simp_p: simp_p, simp_c = price, combo
        if best_c:
            rns = rns_c if rns_c else best_c
            simp = simp_c if simp_c else rns
            result[db_key] = (best_c, rns, simp)
    return result

# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif;
  background: #f0f2ff;
  min-height: 100vh;
  -webkit-tap-highlight-color: transparent;
  overscroll-behavior: none;
}

/* ---- TOP BAR ---- */
.top-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #FF6B6B;
  padding: 14px 16px 14px 16px;
  padding-top: max(14px, env(safe-area-inset-top));
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.20);
}

#back-btn {
  background: rgba(255,255,255,0.28);
  border: none;
  border-radius: 50%;
  width: 42px;
  height: 42px;
  font-size: 20px;
  cursor: pointer;
  color: white;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  display: none;
}
#back-btn.show { display: flex; }

.top-title {
  font-size: 20px;
  font-weight: 900;
  color: white;
  flex: 1;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- TOC ---- */
#toc-view { padding: 16px 12px 30px; }

.toc-header {
  text-align: center;
  padding: 20px 16px 16px;
  background: linear-gradient(135deg, #FF6B6B 0%, #FFB347 100%);
  border-radius: 18px;
  margin-bottom: 16px;
  color: white;
}
.toc-header h2 { font-size: 22px; font-weight: 900; margin-bottom: 4px; }
.toc-header p { font-size: 15px; opacity: 0.9; font-weight: 600; }

.poke-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
  max-width: 960px;
  margin: 0 auto;
}

.poke-thumb {
  background: white;
  border-radius: 18px;
  padding: 14px 8px 10px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.09);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  transition: transform 0.12s, box-shadow 0.12s;
  -webkit-user-select: none;
}
.poke-thumb:active { transform: scale(0.93); box-shadow: 0 1px 4px rgba(0,0,0,0.10); }

.thumb-circle {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.thumb-circle img {
  width: 82px;
  height: 82px;
  object-fit: contain;
}

.thumb-name {
  font-size: 13px;
  font-weight: 800;
  color: #333;
  line-height: 1.2;
  max-width: 110px;
}
.thumb-num {
  font-size: 11px;
  color: #aaa;
  font-weight: 600;
}

/* ---- DETAIL VIEW ---- */
#detail-view { display: none; padding-bottom: 30px; }

.card-banner {
  padding: 24px 20px 0;
  text-align: center;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  position: relative;
  overflow: hidden;
}
.banner-circle1 {
  position: absolute; top: -30px; right: -20px;
  width: 180px; height: 180px;
  background: rgba(255,255,255,0.10); border-radius: 50%;
}
.banner-circle2 {
  position: absolute; bottom: 30px; left: -20px;
  width: 110px; height: 110px;
  background: rgba(255,255,255,0.08); border-radius: 50%;
}

.poke-art {
  width: 150px;
  height: 150px;
  object-fit: contain;
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 6px 16px rgba(0,0,0,0.22));
}
.poke-title {
  font-size: 34px;
  font-weight: 900;
  color: white;
  text-shadow: 0 2px 6px rgba(0,0,0,0.20);
  position: relative;
  z-index: 1;
  margin-bottom: 6px;
  margin-top: 8px;
}
.recipe-pill {
  background: rgba(0,0,0,0.22);
  border-radius: 22px;
  padding: 7px 20px;
  color: white;
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 18px;
  position: relative;
  z-index: 1;
}

/* ---- RECIPE ROWS ---- */
.recipe-section {
  margin: 14px 14px 0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.09);
}

.row-label {
  padding: 11px 16px;
  font-size: 16px;
  font-weight: 900;
  color: white;
}
.row-label.rainbow { background: #6A1B9A; }
.row-label.everyday { background: #BF360C; }
.row-label.legendary-lbl { background: #B8860B; }

.ing-row {
  background: white;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  padding: 10px 6px 6px;
  gap: 2px;
}

.ing-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 2px 18px;
  position: relative;
  gap: 4px;
}
.ing-img {
  width: 58px;
  height: 58px;
  object-fit: contain;
}
.ing-name {
  font-size: 11px;
  font-weight: 700;
  color: #333;
  text-align: center;
  line-height: 1.2;
}
.ing-badge {
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: white;
  font-size: 13px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
}

.legendary-note {
  background: white;
  padding: 24px 20px;
  text-align: center;
  color: #666;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.6;
}

.count-prompt {
  text-align: center;
  padding: 16px 12px 6px;
  color: #555;
  font-size: 16px;
  font-weight: 800;
}

.card-footer {
  text-align: center;
  padding: 10px;
  color: #ccc;
  font-size: 12px;
  margin-top: 6px;
}
"""

JS = r"""
const ING = {
  1:  {name:"Tiny Mushroom",  slug:"tinymushroom"},
  2:  {name:"Big Root",       slug:"bigroot"},
  3:  {name:"Bluk Berry",     slug:"blukberry"},
  4:  {name:"Icy Rock",       slug:"icyrock"},
  5:  {name:"Apricorn",       slug:"apricorn"},
  6:  {name:"Honey",          slug:"honey"},
  7:  {name:"Fossil",         slug:"fossil"},
  8:  {name:"Balm Mushroom",  slug:"balmmushroom"},
  9:  {name:"Rainbow Matter", slug:"rainbowmatter"},
  10: {name:"Mystical Shell", slug:"mysticalshell"}
};
const ING_BASE = "https://raw.githubusercontent.com/gianemi2/pokemon-quest-recipes-maker/master/assets/ingredient-image";
const ART_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork";

function ingUrl(id) { return `${ING_BASE}/${ING[id].slug}.png`; }
function artUrl(dex) { return `${ART_BASE}/${dex}.png`; }

function ingRowHTML(ids, label, labelClass, badgeColor) {
  const cards = ids.map((id,i) => `
    <div class="ing-card">
      <img class="ing-img" src="${ingUrl(id)}" alt="${ING[id].name}" loading="lazy">
      <span class="ing-name">${ING[id].name}</span>
      <span class="ing-badge" style="background:${badgeColor}">${i+1}</span>
    </div>`).join('');
  return `<div class="recipe-section">
    <div class="row-label ${labelClass}">${label}</div>
    <div class="ing-row">${cards}</div>
  </div>`;
}

function renderDetail(p) {
  const rowA = p.is_legendary
    ? ingRowHTML(p.row_a, '&#9733; Legendary Recipe &mdash; Mystical Shell', 'legendary-lbl', p.color)
    : ingRowHTML(p.row_a, '&#9733; With Rainbow Matter', 'rainbow', p.color);

  const rowB = p.is_legendary
    ? `<div class="recipe-section">
         <div class="row-label everyday">&#9679; Everyday Ingredients</div>
         <div class="legendary-note">
           This Legendary can only be cooked<br>with 5 Mystical Shells.<br>
           <strong>No everyday substitute exists!</strong>
         </div>
       </div>`
    : ingRowHTML(p.row_b, '&#9679; Everyday Ingredients', 'everyday', p.color);

  const prompt = p.is_legendary ? '' :
    `<p class="count-prompt">Count 5 ingredients in each row &mdash; can you do it? &#9733;</p>`;

  return `
    <div class="card-banner" style="background:${p.color}">
      <div class="banner-circle1"></div>
      <div class="banner-circle2"></div>
      <img class="poke-art" src="${artUrl(p.dex)}" alt="${p.name}">
      <div class="poke-title">${p.name}</div>
      <div class="recipe-pill">Cook a ${p.recipe}!</div>
    </div>
    ${rowA}
    ${rowB}
    ${prompt}
    <p class="card-footer">#${String(p.dex).padStart(3,'0')} &bull; Pok&eacute;mon Quest Cooking Book</p>`;
}

function showTOC() {
  document.getElementById('toc-view').style.display = '';
  document.getElementById('detail-view').style.display = 'none';
  document.getElementById('back-btn').classList.remove('show');
  document.querySelector('.top-title').textContent = 'Pokemon Cooking Book';
  window.scrollTo(0, 0);
}

function showPokemon(id) {
  const p = POKEMON.find(x => x.id === id);
  if (!p) { showTOC(); return; }
  const dv = document.getElementById('detail-view');
  dv.innerHTML = renderDetail(p);
  dv.style.display = '';
  document.getElementById('toc-view').style.display = 'none';
  document.getElementById('back-btn').classList.add('show');
  document.querySelector('.top-title').textContent = p.name;
  window.scrollTo(0, 0);
}

function navigate(id) {
  if (id) location.hash = id;
  else { history.pushState('', document.title, location.pathname + location.search); showTOC(); }
}

document.getElementById('back-btn').addEventListener('click', () => navigate(''));
window.addEventListener('hashchange', () => {
  const id = location.hash.slice(1);
  if (id) showPokemon(id); else showTOC();
});

// Build TOC grid
const grid = document.getElementById('poke-grid');
grid.innerHTML = POKEMON.map(p => `
  <div class="poke-thumb" onclick="navigate('${p.id}')">
    <div class="thumb-circle" style="background:${p.color}22">
      <img src="${artUrl(p.dex)}" alt="${p.name}" loading="lazy">
    </div>
    <span class="thumb-name">${p.name}</span>
    <span class="thumb-num">#${String(p.dex).padStart(3,'0')}</span>
  </div>`).join('');

// Initial route
const initHash = location.hash.slice(1);
if (initHash) showPokemon(initHash); else showTOC();
"""

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Poke Cooking">
  <meta name="theme-color" content="#FF6B6B">
  <link rel="manifest" href="manifest.json">
  <link rel="apple-touch-icon" href="icon.png">
  <title>Pokemon Quest Cooking Book</title>
  <style>{css}</style>
</head>
<body>
  <div class="top-bar">
    <button id="back-btn" aria-label="Back">&#8592;</button>
    <span class="top-title">Pokemon Cooking Book</span>
  </div>

  <div id="toc-view">
    <div class="toc-header">
      <h2>&#127859; Pokemon Cooking Book</h2>
      <p>Tap a Pokemon to see their recipe!</p>
    </div>
    <div id="poke-grid" class="poke-grid"></div>
  </div>

  <div id="detail-view"></div>

  <script>
const POKEMON = {pokemon_json};
{js}
  </script>
</body>
</html>
"""

MANIFEST = {
    "name": "Pokemon Quest Cooking Book",
    "short_name": "Poke Cooking",
    "description": "Kid-friendly Pokemon Quest recipe guide",
    "start_url": ".",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#f0f2ff",
    "theme_color": "#FF6B6B",
    "icons": [
        {"src": "icon.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
    ]
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 58)
    print("Pokemon Quest Cooking Book  — Web Generator")
    print("=" * 58)

    print("\n[1/4] Fetching game data ...")
    poke_text   = fetch("https://raw.githubusercontent.com/justingolden21/pquest/main/js/pokeData.js")
    recipe_text = fetch("https://raw.githubusercontent.com/gianemi2/pokemon-quest-recipes-maker/master/database/recipeDatabase.js", 0.5)
    all_text    = fetch("https://raw.githubusercontent.com/gianemi2/pokemon-quest-recipes-maker/master/database/allRecipesDatabase.js", 0.5)
    if not all([poke_text, recipe_text, all_text]):
        print("ERROR: data fetch failed"); return

    print("[2/4] Parsing ...")
    specific_recipe, color_map = parse_poke_data(poke_text)
    db_recipe = parse_recipe_db(recipe_text)
    combos    = parse_combos(all_text)
    print(f"  Recipes: {len(specific_recipe)}  DB: {len(db_recipe)}  Combos: {len(combos)}/18")

    print("[3/4] Building Pokemon data ...")
    pokemon_list = []
    for idx, (dex_num, display_name, poke_key) in enumerate(OBTAINABLE):
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
        combo_data  = combos.get(db_key)
        if combo_data:
            best_ids, rns_ids, simple_ids = combo_data
        else:
            best_ids = rns_ids = simple_ids = [6, 6, 8, 8, 1]

        is_legendary = dex_num in LEGENDARY_DEX
        row_a = best_ids if is_legendary else rns_ids
        row_b = simple_ids

        color = BANNER_COLORS[idx % len(BANNER_COLORS)]
        pokemon_list.append({
            "id": f"p{dex_num}",
            "dex": dex_num,
            "name": display_name,
            "recipe": recipe_name,
            "color": color,
            "is_legendary": is_legendary,
            "row_a": row_a,
            "row_b": row_b,
        })
        print(f"  #{dex_num:3d} {display_name:15s} → {recipe_name}")

    print("[4/4] Writing files ...")
    web_dir = Path("web")
    web_dir.mkdir(exist_ok=True)

    # Generate HTML
    html = HTML_TEMPLATE.format(
        css=CSS,
        pokemon_json=json.dumps(pokemon_list, ensure_ascii=False),
        js=JS,
    )
    (web_dir / "index.html").write_text(html, encoding="utf-8")

    # Manifest
    (web_dir / "manifest.json").write_text(json.dumps(MANIFEST, indent=2), encoding="utf-8")

    # Download Pikachu as PWA icon
    icon_path = web_dir / "icon.png"
    if not icon_path.exists():
        try:
            r = session.get(
                "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png",
                timeout=20
            )
            if r.status_code == 200:
                icon_path.write_bytes(r.content)
                print("  Downloaded Pikachu icon")
        except Exception as e:
            print(f"  WARN icon download: {e}")

    print("\n" + "=" * 58)
    print("DONE")
    print(f"  {len(pokemon_list)} Pokemon  •  web/index.html  •  web/manifest.json")
    print("=" * 58)


if __name__ == "__main__":
    main()
