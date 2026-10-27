"""Score an extractor against ground-truth labels (field-level accuracy, speed, cost)."""
import argparse
import json
import os
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from app.extraction.rules import extract_with_rules

load_dotenv()

FIELDS = ["vendor_name", "currency", "invoice_number", "invoice_date",
          "due_date", "po_number", "subtotal", "tax", "total"]


def match(expected, got):
    if expected is None or got is None:
        return expected is None and got is None
    if isinstance(expected, float):
        return abs(expected - got) < 0.01
    return str(expected).strip() == str(got).strip()


def load_extractor(name):
    """Import lazily so you only need the packages/keys for the extractor you use."""
    if name == "ollama":
        from app.extraction.local import USAGE, extract_with_ollama
        return USAGE, extract_with_ollama
    if name == "gemini":
        from app.extraction.gemini import USAGE, extract_with_gemini
        return USAGE, extract_with_gemini
    if name == "llm":
        from app.extraction.llm import USAGE, extract_with_llm
        return USAGE, extract_with_llm
    return None, extract_with_rules


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="data/labels/labels.json")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--extractor", choices=["rules", "ollama", "gemini", "llm"], default="rules")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--start", type=int, default=0, help="first invoice index (0-based)")
    ap.add_argument("--end", type=int, default=None, help="stop before this index")
    args = ap.parse_args()

    USAGE, extractor = load_extractor(args.extractor)

    labels = json.loads(Path(args.labels).read_text())
    labels = labels[args.start:args.end]
    if args.limit:
        labels = labels[: args.limit]
    raw = Path(args.raw)

    field_ok = defaultdict(int)
    grp_ok, grp_n = defaultdict(int), defaultdict(int)
    perfect, errors, misses = 0, 0, []
    start = time.time()

    for lab in labels:
        group = "scanned" if lab.get("scanned") else lab["layout"]
        try:
            got = extractor(raw / lab["file"]).model_dump()
        except Exception as e:
            errors += 1
            print(f"  ERROR {lab['file']}: {type(e).__name__}: {e}")
            got = {f: None for f in FIELDS}
        doc_ok = True
        for f in FIELDS:
            ok = match(lab["fields"][f], got[f])
            field_ok[f] += ok
            grp_ok[group] += ok
            if not ok:
                doc_ok = False
                if len(misses) < 8:
                    misses.append((lab["file"], f, lab["fields"][f], got[f]))
        grp_n[group] += len(FIELDS)
        perfect += doc_ok

    n = len(labels)
    secs = time.time() - start
    print(f"\nExtractor: {args.extractor}  |  Documents: {n}  |  Errors: {errors}")
    print(f"Time: {secs:.1f}s total, {secs / n:.2f}s per invoice")
    print(f"Fully correct documents: {perfect}/{n} ({perfect / n:.0%})\n")
    print("Field accuracy:")
    for f in FIELDS:
        print(f"  {f:16s} {field_ok[f] / n:6.1%}")
    print("\nBy group:")
    for k in grp_n:
        print(f"  {k:14s} {grp_ok[k] / grp_n[k]:6.1%}")

    if USAGE:
        print(f"\nTokens: {USAGE['input_tokens']:,} in / {USAGE['output_tokens']:,} out "
              f"({USAGE['image_calls']} image calls)")
        pin = float(os.getenv("PRICE_IN_PER_MTOK", 0))
        pout = float(os.getenv("PRICE_OUT_PER_MTOK", 0))
        if pin or pout:
            cost = USAGE["input_tokens"] / 1e6 * pin + USAGE["output_tokens"] / 1e6 * pout
            print(f"Cost: ${cost:.4f} total, ${cost / n:.5f} per invoice")

    if misses:
        print("\nSample misses (file, field, expected, got):")
        for m in misses:
            print("  ", m)


if __name__ == "__main__":
    main()