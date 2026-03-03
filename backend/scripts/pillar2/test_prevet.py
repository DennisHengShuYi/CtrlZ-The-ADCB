"""
Test invoice pre-vet with demo invoices.
Run from backend/: python -m scripts.pillar2.test_prevet [invoice_file]
  - No args: test demo_invoice.json
  - --all: test all demo invoices in data/pillar2/demo_invoices/
  - filename: test specific file
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")

from app.pillar2.invoice_prevet import pre_vet_invoice

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = _BACKEND_DIR / "data" / "pillar2"
DEMO_INVOICE = DATA_DIR / "demo_invoice.json"
DEMO_INVOICES_DIR = DATA_DIR / "demo_invoices"


def run_prevet(invoice_path: Path) -> None:
    with open(invoice_path, encoding="utf-8") as f:
        invoice = json.load(f)

    print(f"\n{'='*60}")
    print(f"Pre-vetting: {invoice_path.name}")
    print("=" * 60)
    result = pre_vet_invoice(invoice)

    print(f"Invoice: {result['invoice_id']}")
    print(f"Total tariff: {result['total_tariff']}")
    print(f"Requires HITL: {result['any_requires_hitl']}")
    if result["all_flags"]:
        print("Flags:", result["all_flags"])

    print("\nLine items:")
    for item in result["line_items"]:
        hitl = " [HITL]" if item["requires_hitl"] else ""
        print(f"  {item['item_id']}: {item['description'][:40]:40} -> {item['ahtn_code']} "
              f"(sim={item['similarity']:.2f}){hitl}")
        if item["flags"]:
            for flag in item["flags"]:
                print(f"       ⚠ {flag}")


def main() -> None:
    if "--all" in sys.argv:
        paths = sorted(DEMO_INVOICES_DIR.glob("*.json")) if DEMO_INVOICES_DIR.exists() else []
        if not paths:
            print("No demo invoices found in data/pillar2/demo_invoices/")
            return
        for p in paths:
            run_prevet(p)
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        path = Path(sys.argv[1])
        if not path.is_absolute():
            path = DATA_DIR / path
        if not path.exists():
            print(f"File not found: {path}")
            return
        run_prevet(path)
    else:
        path = DEMO_INVOICE if DEMO_INVOICE.exists() else DEMO_INVOICES_DIR / "invoice_food_beverages.json"
        if not path.exists():
            print("No demo invoice found. Create backend/data/pillar2/demo_invoice.json or add files to demo_invoices/")
            return
        run_prevet(path)


if __name__ == "__main__":
    main()
