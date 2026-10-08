import re
from unidecode import unidecode
from nltk.stem import WordNetLemmatizer

from app.vocabulary.product_types import PRODUCT_TYPES

# Lemmatizing instead of stemming, stemming turns "leaves" into "leav"
# https://www.nltk.org/api/nltk.stem.WordNetLemmatizer.html
# https://www.ibm.com/topics/stemming-lemmatization
lemmatizer = WordNetLemmatizer()

# Starter list proposed by Claude Opus 5.5 from common grocery labels
# Sizes and packaging from ingredient-parser, claims from OFF's labels taxonomy
# https://github.com/strangetom/ingredient-parser/blob/master/ingredient_parser/en/_constants.py
# https://github.com/openfoodfacts/openfoodfacts-server/blob/main/taxonomies/labels.txt
# Not "whole" (whole milk), "a" (vitamin a), "wild" (wild rice), "kosher" (kosher salt) or "pound" (pound cake)
strip_words = {
    "pc", "president's", "choice", "no", "name", "great", "value", "compliment", "selection", "kirkland",
    "g", "kg", "ml", "l", "lb", "oz", "fl", "ct", "count", "dozen", "ounce", "litre", "liter", "kilogram",
    "gallon", "pint", "quart",
    "pack", "package", "packet", "bag", "bottle", "box", "can", "jar", "tub", "tin", "punnet", "sachet",
    "small", "medium", "large", "extra", "jumbo", "big", "little", "tiny", "mini", "regular", "thick", "thin",
    "organic", "fresh", "free", "run", "range", "grade", "natural", "local",
    "non", "gmo", "fair", "trade", "halal", "grass", "fed", "cage", "pasture", "raised", "antibiotic", "hormone",
    "chopped", "sliced", "diced", "shredded", "grated",
}


def clean(name: str):
    # Removes accents ("jalapeño" -> "jalapeno")
    # https://pypi.org/project/Unidecode/
    plain = unidecode(name).lower()

    # Punctuation becomes a space ("free-run" -> "free run"), "%" and "'" stay for "2%" and "president's"
    # https://docs.python.org/3/library/re.html#re.sub
    # https://stackoverflow.com/questions/1276764/stripping-everything-but-alphanumeric-chars-from-a-string-in-python/1276774#1276774
    plain = re.sub(r"[^a-z0-9%']+", " ", plain)

    words = []
    for word in plain.split():
        words.append(lemmatizer.lemmatize(word))
    return words


# Looks up a type by any of its names, cleaned like the user's input so "Grits" and "grits" both become "grit"
names_to_keys = {}
for key, product_type in PRODUCT_TYPES.items():
    for name in [product_type["name"]] + product_type["synonyms"]:
        names_to_keys.setdefault(" ".join(clean(name)), key)


# Exact matches only, so "sour cream" never becomes "cream"
def normalize_name(name: str):
    words = clean(name)

    key = names_to_keys.get(" ".join(words))
    if key:
        return key, "alias"

    kept = []
    for word in words:
        if word in strip_words:
            continue
        # Sizes start with a number ("2%", "500g")
        # https://docs.python.org/3/library/stdtypes.html#str.isdigit
        if word[0].isdigit():
            continue
        kept.append(word)

    key = names_to_keys.get(" ".join(kept))
    if key:
        return key, "strip"

    return None, None
