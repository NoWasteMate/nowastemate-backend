text = open("scripts/ingredients.txt").read()

text_blocks = text.split("\n\n")
print(len(text_blocks))

for block in text_blocks:
    names = []
    parents = []

    for line in block.split("\n"):
        if line.startswith("en: "):
            names = line[4:].split(", ")
        elif line.startswith("< en: "):
            parents.append(line[6:])
    if names and parents:
        print(names, parents)
        # break
