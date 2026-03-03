"""
Test AHTN RAG with chapter-based filtering.
Run from backend/: python -m scripts.pillar2.test_ahtn
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")

from app.pillar2.ahtn_hints import CHAPTER_HINTS, HEADING_HINTS
from app.pillar2.ahtn_search import search_ahtn


def pick_best(desc: str, results: list[dict]) -> dict:
    desc_lower = desc.lower()
    for (h1, h2), heading in HEADING_HINTS.items():
        if h1 in desc_lower and h2 in desc_lower:
            for r in results:
                if r["ahtn_code"].startswith(heading):
                    return r
    for hint, chapter in CHAPTER_HINTS.items():
        if hint in desc_lower:
            if "glove" in desc_lower:
                for r in results:
                    if r["ahtn_code"].startswith(chapter) and "glove" in r.get("description", "").lower():
                        return r
            for r in results:
                if r["ahtn_code"].startswith(chapter):
                    return r
    return results[0]


def main() -> None:
    test_products = [
        "Genuine leather handbag, women's fashion",
        "Chocolate-coated biscuits, halal certified",
        "Cotton t-shirts, men's casual wear",
        "Rubber gloves, disposable",
    ]

    for desc in test_products:
        results = search_ahtn(desc, top_k=50)
        best = pick_best(desc, results)
        print(f"{desc[:45]:45} -> {best['ahtn_code']} ({best['description'][:50]}...)")


if __name__ == "__main__":
    main()
