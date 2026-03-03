"""
Query expansion to improve embedding similarity with AHTN descriptions.

Adds common synonyms/aliases so "Smartphone" matches "mobile phone" in AHTN text.
"""

# Product term → additional keywords to append (from AHTN / HS terminology)
# More terms = better Sim, but avoid irrelevant words that could hurt matching
QUERY_SYNONYMS: dict[str, list[str]] = {
    "smartphone": ["mobile phone", "cellular phone", "handheld", "transmission apparatus", "telephone", "electrical"],
    "phone": ["mobile", "cellular", "telephone", "transmission", "electrical", "apparatus"],
    "headphone": ["earphone", "headset", "audio", "loudspeaker", "electrical", "whether or not"],
    "headphones": ["earphones", "headset", "audio", "loudspeaker", "electrical", "whether or not"],
    "wireless": ["radio", "electrical", "transmission"],
    "bluetooth": ["wireless", "radio", "electrical", "headset"],
    "cable": ["conductor", "wire", "electrical", "data cable", "flat", "lines"],
    "usb": ["conductor", "cable", "electrical", "data", "flat", "charging"],
    "charging": ["power", "electrical", "conductor", "cable", "data"],
    "handbag": ["bag", "travel goods", "leather", "outer surface"],
    "biscuit": ["bakers", "cereal", "flour", "bread"],
    "biscuits": ["bakers", "cereal", "flour", "bread"],
    "chocolate": ["cocoa", "sweet", "confectionery"],
    "t-shirt": ["shirt", "vest", "singlet", "knitted", "apparel"],
    "t-shirts": ["shirts", "vests", "singlets", "knitted", "apparel"],
    "glove": ["gloves", "mittens", "mitts", "vulcanised", "rubber"],
    "gloves": ["mittens", "mitts", "vulcanised", "rubber"],
    "knife": ["cutlery", "blade", "kitchen"],
    "knives": ["cutlery", "blade", "kitchen"],
    "mug": ["ceramic", "tableware", "household", "pottery"],
    "container": ["plastic", "receptacle", "article"],
    "board": ["wood", "bamboo", "kitchen", "household"],
    "blouse": ["shirt", "apparel", "knitted", "women"],
    "jeans": ["trousers", "pants", "denim", "woven", "apparel"],
    "blanket": ["bedding", "textile", "fabric"],
    "sugar": ["sucrose", "sweetener", "sugar"],
    "coffee": ["extract", "preparation", "beverage"],
    "pineapple": ["fruit", "edible", "preserved"],
    "canned": ["preserved", "prepared", "fruit", "vegetable"],
    "mask": ["breathing", "medical", "surgical", "respirator"],
    "tablet": ["medicament", "pharmaceutical", "medicine"],
    "paracetamol": ["medicament", "analgesic", "pharmaceutical"],
}


def expand_query(query: str) -> str:
    """
    Expand product description with synonyms to improve AHTN embedding match.
    Returns: original query + space + additional relevant terms.
    """
    query_lower = query.lower()
    extra_terms: list[str] = []
    seen: set[str] = set()

    for term, synonyms in QUERY_SYNONYMS.items():
        if term in query_lower:
            for syn in synonyms:
                if syn not in seen and syn not in query_lower:
                    extra_terms.append(syn)
                    seen.add(syn)

    if not extra_terms:
        return query
    return f"{query} {' '.join(extra_terms)}"
