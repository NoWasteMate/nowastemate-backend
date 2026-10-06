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
for entry in entries:
    for name in entry["names"]:
        by_name[name.lower()] = entry

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


# ----- Debug -----

def debug_top_level():
    top_level = []

    for entry in entries:
        if not entry["parents"]:
            top_level.append(entry["names"][0])

    print(f"Length: {len(top_level)}, Top Level: {sorted(top_level)}")

#
# for name in ["cheddar", "carrot", "chicken breast", "orange juice", "chicken egg", "salt"]:
#     print(f"{name}: {find_category(by_name[name])}")

# print(find_category(by_name.get("apple")))
