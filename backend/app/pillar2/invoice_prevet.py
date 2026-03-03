"""
Invoice pre-vet service: RAG + LLM refiner + confidence + tariff + flags.

Flow: Invoice JSON → AHTN lookup → (hints or LLM) pick best code → tariff calc → flags → HITL routing.
"""

import os
import re
from typing import Any

from openai import OpenAI

from app.pillar2.ahtn_hints import CHAPTER_HINTS, HEADING_HINTS
from app.pillar2.ahtn_search import search_ahtn

CONFIDENCE_THRESHOLD = 0.75  # Cosine similarity; tune based on accuracy needs (0.9 = strict)
TOP_K = 50  # Higher for heading hints (e.g. 4015 rubber gloves) to appear in results


def _pick_best_by_hints(desc: str, results: list[dict]) -> dict | None:
    """
    Pick best AHTN code using chapter/heading hints when they match.
    Returns None if no hints match (caller should use LLM).
    """
    desc_lower = desc.lower()
    # Heading-level hints first (most specific)
    for (h1, h2), heading in HEADING_HINTS.items():
        if h1 in desc_lower and h2 in desc_lower:
            for r in results:
                if r["ahtn_code"].startswith(heading):
                    return r
    # Chapter hints
    for hint, chapter in CHAPTER_HINTS.items():
        if hint in desc_lower:
            # For gloves: prefer results with "glove" in description (avoids latex vs gloves)
            if "glove" in desc_lower:
                for r in results:
                    if r["ahtn_code"].startswith(chapter) and "glove" in r.get("description", "").lower():
                        return r
            for r in results:
                if r["ahtn_code"].startswith(chapter):
                    return r
    return None


def _parse_rate(rate_str: str) -> float:
    """Parse AHTN rate (e.g. '5%', '0%') to float."""
    if not rate_str:
        return 0.0
    match = re.search(r"([\d.]+)\s*%", str(rate_str))
    return float(match.group(1)) / 100 if match else 0.0


def _llm_pick_best(product_desc: str, candidates: list[dict]) -> dict | None:
    """
    LLM picks the best AHTN code from RAG candidates.
    Returns the chosen candidate dict, or None if LLM fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    options = "\n".join(
        [
            f"- {r['ahtn_code']}: {r['description']} (duty: {r.get('rate', 'N/A')})"
            for r in candidates[:10]
        ]
    )
    prompt = f"""Product description: {product_desc}

AHTN candidates from database:
{options}

Which AHTN code is correct for this product? Reply with ONLY the code (e.g. 4202.21.00), nothing else."""

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
        )
        chosen = response.choices[0].message.content.strip()
        code_match = re.search(r"\d{4}\.\d{2}(?:\.\d{2})?(?:\.\d{2})?", chosen)
        if code_match:
            code = code_match.group(0).replace(" ", "")
            for r in candidates:
                if r["ahtn_code"] == code:
                    return r
            for r in candidates:
                if r["ahtn_code"].startswith(code) or code.startswith(r["ahtn_code"][:7]):
                    return r
            for r in candidates:
                if r["ahtn_code"][:4] == code[:4]:
                    return r
    except Exception:
        pass
    return candidates[0] if candidates else None


def _check_flags(
    description: str,
    ahtn_code: str,
    buyer_country: str,
) -> list[str]:
    """Flag inconsistencies (e.g. Halal cert for food to Indonesia)."""
    flags: list[str] = []
    desc_lower = description.lower()

    chapter = ahtn_code[:2] if len(ahtn_code) >= 2 else ""
    is_food = chapter.isdigit() and 2 <= int(chapter) <= 24
    food_keywords = ["biscuit", "chocolate", "snack", "halal", "food", "candy", "meat", "fish"]
    looks_like_food = any(kw in desc_lower for kw in food_keywords) or is_food

    if buyer_country == "ID" and looks_like_food:
        flags.append("Warning: This product may require Halal certification for Indonesia.")

    return flags


def pre_vet_invoice(invoice: dict[str, Any]) -> dict[str, Any]:
    """
    Pre-vet an invoice: classify each line item, calculate tariffs, flag issues.

    Args:
        invoice: Invoice JSON (from OCR or manual input)

    Returns:
        Pre-vet result with classified line items, tariffs, HITL flags.
    """
    line_items = invoice.get("line_items", [])
    buyer_country = invoice.get("buyer", {}).get("country", "")

    classified: list[dict] = []
    all_flags: list[str] = []
    total_tariff = 0.0
    any_requires_hitl = False

    for item in line_items:
        desc = item.get("description", "")
        amount = float(item.get("amount", 0))
        item_id = item.get("item_id", 0)

        results = search_ahtn(desc, top_k=TOP_K)
        if not results:
            classified.append({
                "item_id": item_id,
                "description": desc,
                "quantity": item.get("quantity"),
                "unit": item.get("unit", ""),
                "unit_price": float(item.get("unit_price", 0)),
                "amount": amount,
                "origin_country": item.get("origin_country", ""),
                "ahtn_code": "UNKNOWN",
                "ahtn_description": "",
                "tariff_rate": "0%",
                "tariff_amount": 0.0,
                "similarity": 0.0,
                "requires_hitl": True,
                "flags": ["No AHTN match found"],
            })
            any_requires_hitl = True
            continue

        best = _pick_best_by_hints(desc, results)
        if best is None:
            best = _llm_pick_best(desc, results)
        if best is None:
            best = results[0]

        similarity = best.get("similarity", 0.0)
        rate_str = best.get("rate", "0%")
        rate_val = _parse_rate(rate_str)
        tariff_amount = amount * rate_val

        requires_hitl = similarity < CONFIDENCE_THRESHOLD

        flags = _check_flags(desc, best.get("ahtn_code", ""), buyer_country)
        all_flags.extend(flags)

        if requires_hitl:
            any_requires_hitl = True

        classified.append({
            "item_id": item_id,
            "description": desc,
            "quantity": item.get("quantity"),
            "unit": item.get("unit", ""),
            "unit_price": float(item.get("unit_price", 0)),
            "amount": amount,
            "origin_country": item.get("origin_country", ""),
            "ahtn_code": best.get("ahtn_code", ""),
            "ahtn_description": best.get("description", ""),
            "tariff_rate": rate_str,
            "tariff_amount": round(tariff_amount, 2),
            "similarity": round(similarity, 4),
            "requires_hitl": requires_hitl,
            "flags": flags,
        })

        total_tariff += tariff_amount

    return {
        "invoice_id": invoice.get("invoice_id", ""),
        "line_items": classified,
        "total_tariff": round(total_tariff, 2),
        "any_requires_hitl": any_requires_hitl,
        "all_flags": list(dict.fromkeys(all_flags)),
    }
