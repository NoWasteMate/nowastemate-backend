text = open("scripts/ingredients.txt").read()

text_blocks = text.split("\n\n")

names_prefix = "en: "
parents_prefix = "< en: "
allergen_prefix = "allergens:en: en:"
vegan_prefix = "vegan:en: "
vegetarian_prefix = "vegetarian:en: "

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


by_name = {}

for entry in entries:
    for name in entry["names"]:
        by_name[name.lower()] = entry


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




# ----- Debug -----

def debug_top_level():
    top_level = []

    for entry in entries:
        if not entry["parents"]:
            top_level.append(entry["names"][0])

    print(f"Length: {len(top_level)}, Top Level: {sorted(top_level)}")


debug_top_level()

print(find_flag(by_name["chicken egg"], "vegan"))
print(find_flag(by_name["chicken egg"], "vegetarian"))
print(find_flag(by_name["vegetable shortening"], "vegan"))
