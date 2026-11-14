from app.vocabulary.off_product_types import OFF_PRODUCT_TYPES

PRODUCT_TYPES = OFF_PRODUCT_TYPES

# Hand edited additions, kept out of off_product_types.py because the import script rewrites that file
# Types the OFF list doesn't have, found the same way as the synonyms below
# Category and diet flags are copied from the parent like scripts/OFF_types.py does, as OFF has
# "minced beef" under "beef meat" and "ground nutmeg" under "nutmeg"
# The sodas are "beverage" by hand, their parent "carbonated water" is "other"
EXTRA_TYPES = {
    "ground-turkey": {
        "name": "ground turkey", "parents": ["turkey-meat"], "synonyms": ["minced turkey"],
        "category": "meat", "allergens": [],
        "vegan": "no", "vegetarian": "no", "glutenFree": "maybe",
    },
    "ground-cinnamon": {
        "name": "ground cinnamon", "parents": ["cinnamon"], "synonyms": [],
        "category": "other", "allergens": [],
        "vegan": "yes", "vegetarian": "yes", "glutenFree": "maybe",
    },
    "ground-cumin": {
        "name": "ground cumin", "parents": ["cumin"], "synonyms": [],
        "category": "other", "allergens": [],
        "vegan": "yes", "vegetarian": "yes", "glutenFree": "maybe",
    },
    "minced-garlic": {
        "name": "minced garlic", "parents": ["garlic"], "synonyms": [],
        "category": "produce", "allergens": [],
        "vegan": "yes", "vegetarian": "yes", "glutenFree": "maybe",
    },
    "baking-soda": {
        "name": "baking soda", "parents": [], "synonyms": ["bicarbonate of soda", "sodium bicarbonate"],
        "category": "other", "allergens": [],
        "vegan": "yes", "vegetarian": "yes", "glutenFree": "maybe",
    },
    "chili-flakes": {
        "name": "chili flakes", "parents": ["chili-pepper"],
        "synonyms": ["chilli flakes", "red pepper flakes", "crushed red pepper"],
        "category": "produce", "allergens": [],
        "vegan": "yes", "vegetarian": "yes", "glutenFree": "maybe",
    },
    "italian-seasoning": {
        "name": "italian seasoning", "parents": ["herbs-and-spices"], "synonyms": [],
        "category": "produce", "allergens": [],
        "vegan": "yes", "vegetarian": "yes", "glutenFree": "maybe",
    },
    "soda": {
        "name": "soda", "parents": ["carbonated-water"], "synonyms": ["soft drink"],
        "category": "beverage", "allergens": [],
        "vegan": "maybe", "vegetarian": "maybe", "glutenFree": "maybe",
    },
    "lemon-lime-soda": {
        "name": "lemon lime soda", "parents": ["soda"], "synonyms": [],
        "category": "beverage", "allergens": [],
        "vegan": "maybe", "vegetarian": "maybe", "glutenFree": "maybe",
    },
}

for key, product_type in EXTRA_TYPES.items():
    PRODUCT_TYPES[key] = product_type

# Names with no match in saved recipes and in a list of common ingredients proposed by Claude Opus 5.5
# The OFF list has a type for each of these under a different name
EXTRA_SYNONYMS = {
    "wheat-flour": ["all purpose flour", "plain flour"],
    # OFF uses the British word. Both forms because "cookies" is cleaned to "cooky", not "cookie"
    "biscuit": ["cookie", "cookies"],
    "minced-pork": ["ground pork"],
    "jalapeno-pepper": ["jalapeno"],
    "beef-steak": ["steak"],
}

for key, synonyms in EXTRA_SYNONYMS.items():
    PRODUCT_TYPES[key]["synonyms"].extend(synonyms)

# Bump when the list changes so the app only downloads a new copy when needed
VERSION = 2
