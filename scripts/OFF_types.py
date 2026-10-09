import re
import json
from unidecode import unidecode

# Pinned to OFF commit e3225ff (2026-10-05). To re-import, download a newer one, update this line and review the diff
# https://github.com/openfoodfacts/openfoodfacts-server/blob/e3225fffbc4639101950f71202935e2aab7245ce/taxonomies/food/ingredients.txt
text = open("scripts/ingredients.txt").read()

text_blocks = text.split("\n\n")

names_prefix = "en: "
parents_prefix = "< en: "
allergen_prefix = "allergens:en: en:"
vegan_prefix = "vegan:en: "
vegetarian_prefix = "vegetarian:en: "

# Category roots proposed by Claude Opus 5.5 from OFF's largest branches
# Order matters, first match should win because items like orange juice fall under both juice and fruit for example
category_roots = [
    ("beverage", {"juice", "alcohol"}),
    ("meat", {"meat", "poultry", "fish", "shellfish", "game animal"}),
    ("dairy", {"dairy"}),
    ("grains", {"cereal", "flour", "rice", "bread", "dough"}),
    ("produce", {"vegetable", "fruit", "herb", "mushroom"}),
]

# OFF allergen names to Health Canada's priority allergens
#https://www.canada.ca/en/health-canada/services/food-allergies-intolerances/food-allergies.html
allergen_names = {
    "eggs": "eggs",
    "milk": "milk",
    "mustard": "mustard",
    "peanuts": "peanuts",
    "crustaceans": "crustaceans and molluscs",
    "molluscs": "crustaceans and molluscs",
    "fish": "fish",
    "sesame-seeds": "sesame",
    "soybeans": "soy",
    "nuts": "tree nuts",
}

# Flavourings are added by manufacturers, nobody buys them
dropped_roots = {"flavouring"}

entries = []

for block in text_blocks:
    entry = {
        "names": [],
        "parents": [],
        "allergen": None,
        "vegan": None,
        "vegetarian": None,
    }

    for line in block.split("\n"):
        if line.startswith(names_prefix):
            entry["names"] = line.removeprefix(names_prefix).split(", ")
        elif line.startswith(parents_prefix):
            entry["parents"].append(line.removeprefix(parents_prefix))
        elif line.startswith(allergen_prefix):
            entry["allergen"] = line.removeprefix(allergen_prefix)
        elif line.startswith(vegan_prefix):
            entry["vegan"] = line.removeprefix(vegan_prefix)
        elif line.startswith(vegetarian_prefix):
            entry["vegetarian"] = line.removeprefix(vegetarian_prefix)

    if entry["names"]:
        entries.append(entry)

# Hash map of every name and synonym to its entry
# So parents can be found by name
by_name = {}

# Build lookup hash map
# setdefault so the first entry keeps a shared name, same as the write loop below
for entry in entries:
    for name in entry["names"]:
        by_name.setdefault(name.lower(), entry)

# ---- Functions ----

# Allergens add up and an entry has its own plus every ancestor's
def find_allergens(entry):
    allergens = []
    if entry["allergen"]:
        allergens.append(entry["allergen"])

    for parent_name in entry["parents"]:
        parent = by_name.get(parent_name.lower())
        if parent:
            for allergen in find_allergens(parent):
                if allergen not in allergens:
                    allergens.append(allergen)

    return allergens

def find_flag(entry, flag):

    if entry[flag]:
        return entry[flag]

    found = []

    for parent_name in entry["parents"]:
        parent = by_name.get(parent_name.lower())
        if parent:
            found.append(find_flag(parent, flag))

    if "no" in found:
        return "no"
    if "maybe" in found:
        return "maybe"
    if "yes" in found:
        return "yes"

    return None

# Every name that exists above the entry
# category can match at any level
def find_ancestors(entry):
    ancestors = []

    for parent_name in entry["parents"]:
        parent = by_name.get(parent_name.lower())
        if parent:
            ancestors.append(parent["names"][0])
            ancestors += find_ancestors(parent)

    return ancestors

# Uses the first group that matches in the category
def find_category(entry):
    names = [entry["names"][0]] + find_ancestors(entry)

    for category, roots in category_roots:
        for name in names:
            if name in roots:
                return category

    return "other"

# Drops any OFF allergens that aren't on Health Canada's list (celery, lupin) and gluten, which becomes glutenFree
def map_allergens(off_allergens):
    allergens = []

    for allergen in off_allergens:
        name = allergen_names.get(allergen)
        if name and name not in allergens:
            allergens.append(name)

    return allergens

# OFF only lists gluten where it's present
# Missing data will be listed as "maybe" instead of "yes" by default
def find_gluten_free(entry):
    if "gluten" in find_allergens(entry):
        return "no"
    return "maybe"

# Keys follow OFF's Python SDK get_tag() rule so they match OFF ids ("Crème fraîche" -> "creme-fraiche")
# https://github.com/openfoodfacts/openfoodfacts-python/blob/develop/src/openfoodfacts/utils/text.py
def make_key(name):
    # Turns accented and other non-English letters into their closest ASCII ("è" → "e", "ł" → "l")
    # https://pypi.org/project/Unidecode/
    # https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string/2633310#2633310
    plain = unidecode(name).lower()
    # OFF turns punctuation into "-" ("cow's milk" → "cow-s-milk")
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")

# "salt from Guérande" and "orange juice from concentrate" already have a plain parent (salt, orange juice)
# Found via Opus 5.5 Scan
def keep_entry(entry):
    name = entry["names"][0]
    names = [name] + find_ancestors(entry)

    if dropped_roots.intersection(names):
        return False
    return " from " not in name

# Parents are stored as keys so the app can walk up the tree
# Parents that aren't kept (E-number additives like "E322" live in OFF's additives.txt) are left out
def find_parent_keys(entry):
    keys = []

    for parent_name in entry["parents"]:
        parent = by_name.get(parent_name.lower())
        if parent and keep_entry(parent):
            keys.append(make_key(parent["names"][0]))

    return keys

# ----- Write the generated file loop -----

product_types = {}

# Every name and synonym already given to a type, so one name never points at two types
used_names = set()

for entry in entries:
    if not keep_entry(entry):
        continue

    key = make_key(entry["names"][0])

    # OFF repeats a few blocks according to our Opus 5.5 scan (broccoli, wild blueberry), first one should therefore win
    # Also skips entries whose name is another type's synonym ("pepeiao" is already a synonym of "pepeao")
    if key in product_types or entry["names"][0].lower() in used_names:
        continue

    # Drops synonyms another type already has ("maida" stays on "maida", not "refined wheat flour")
    # and repeats inside the same line ("whole goat milk, whole goat milk")
    synonyms = []
    used_names.add(entry["names"][0].lower())
    for name in entry["names"][1:]:
        if name.lower() not in used_names:
            synonyms.append(name)
            used_names.add(name.lower())

    # Unknown diet flags are "maybe" so they're never treated as safe
    product_types[key] = {
        "name": entry["names"][0],
        "parents": find_parent_keys(entry),
        "synonyms": synonyms,
        "category": find_category(entry),
        "allergens": map_allergens(find_allergens(entry)),
        "vegan": find_flag(entry, "vegan") or "maybe",
        "vegetarian": find_flag(entry, "vegetarian") or "maybe",
        "glutenFree": find_gluten_free(entry),
    }

# Written as JSON, which Python can also read, so the app can import the file
# Tried pformat first but it cut long names in two ("sweetened condensed skimmed " "milk")
# https://docs.python.org/3/library/json.html#json.dumps
header = (
    "# Generated by scripts/OFF_types.py, DON'T EDIT BY HAND\n\n"
)

with open("app/vocabulary/off_product_types.py", "w") as file:
    file.write(header)
    # indent puts each field on its own line, without it the whole list is one line
    file.write("OFF_PRODUCT_TYPES = " + json.dumps(product_types, indent=4) + "\n")
