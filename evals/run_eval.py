"""Score an extractor against ground-truth labels (field-level accuracy)."""
import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from app.extraction.rules import extract_with_rules

FIELDS = ["vendor_name", "currency", "invoice_number", "invoice_date",
          "due_date", "po_number", "subtotal", "tax", "total"]


def match(expected, got):
    if expected is None or got is None:
        return expected is None and got is None
    if isinstance(expected, float):
        return abs(expected - got) < 0.01
    return str(expected).strip() == str(got).strip()


def main(extractor=extract_with_rules):
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="data/labels/labels.json")
    ap.add_argument("--raw", default="data/raw")
    args = ap.parse_args()

    labels = json.loads(Path(args.labels).read_text())
    raw = Path(args.raw)
    field_ok = defaultdict(int)
    grp_ok, grp_n = defaultdict(int), defaultdict(int)
    perfect = 0
    misses = []
    start = time.time()

    for lab in labels:
        got = extractor(raw / lab["file"]).model_dump()
        group = "scanned" if lab.get("scanned") else lab["layout"]
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
    print(f"\nDocuments: {n}  |  time: {time.time() - start:.1f}s")
    print(f"Fully correct documents: {perfect}/{n} ({perfect / n:.0%})\n")
    print("Field accuracy:")
    for f in FIELDS:
        print(f"  {f:16s} {field_ok[f] / n:6.1%}")
    print("\nBy group:")
    for k in grp_n:
        print(f"  {k:14s} {grp_ok[k] / grp_n[k]:6.1%}")
    if misses:
        print("\nSample misses (file, field, expected, got):")
        for m in misses:
            print("  ", m)


if __name__ == "__main__":
    main()