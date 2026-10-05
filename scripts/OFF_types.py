text = open("scripts/ingredients.txt").read()

text_blocks = text.split("\n\n")
print(len(text_blocks))

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

print(len(entries))

by_name = {}

for entry in entries:
    for name in entry["names"]:
        by_name[name.lower()] = entry

print(by_name["eggs"])
print(by_name["chicken egg"])
