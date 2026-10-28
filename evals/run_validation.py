"""Test the validators against the easy dataset's ground truth (labels.json has expected flags)."""
import json
from collections import defaultdict
from pathlib import Path

from app.validation.checks import Validator

labels = json.loads(Path("data/labels/labels.json").read_text())
pos = json.loads(Path("data/labels/purchase_orders.json").read_text())

v = Validator(pos)
tp, fn, fp = defaultdict(int), defaultdict(int), defaultdict(int)
clean_total, clean_flagged = 0, 0
details = []

for lab in labels:
    expected = set(lab["expected_flags"]) - {"prompt_injection"}  # injection is a security test
    got = set(v.check(lab["fields"]))
    if not expected:
        clean_total += 1
        if got:
            clean_flagged += 1
            details.append((lab["file"], "clean but flagged", sorted(got)))
    for f in expected:
        if f in got:
            tp[f] += 1
        else:
            fn[f] += 1
            details.append((lab["file"], f"missed {f}", sorted(got)))
    for f in got - expected:
        fp[f] += 1

print("Flag               caught  missed  extra")
for f in sorted(set(tp) | set(fn) | set(fp)):
    print(f"  {f:22s} {tp[f]:4d} {fn[f]:6d} {fp[f]:6d}")
print(f"\nClean invoices wrongly flagged: {clean_flagged}/{clean_total}")
for d in details[:10]:
    print("  ", d)
