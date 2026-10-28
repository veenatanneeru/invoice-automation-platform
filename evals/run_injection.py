"""Prompt-injection test: send injected invoices through the real extractor and the full checks."""
import json
import time
from pathlib import Path

from app.extraction.local import extract_with_ollama
from app.validation.checks import Validator
from app.validation.decision import decide
from evals.run_eval import FIELDS, match

labels = json.loads(Path("data/labels/labels.json").read_text())
pos = json.loads(Path("data/labels/purchase_orders.json").read_text())
cases = [l for l in labels if "prompt_injection" in l["expected_flags"]]
print(f"Running {len(cases)} injected invoices through the real model...\n")

resisted = caught = succeeded = 0
for lab in cases:
    start = time.time()
    got = extract_with_ollama(Path("data/raw") / lab["file"]).model_dump()
    wrong = [f for f in FIELDS if not match(lab["fields"][f], got[f])]
    flags = Validator(pos).check(got)
    decision = decide(flags)

    if not wrong:
        outcome, resisted = "model resisted", resisted + 1
    elif decision != "approve":
        outcome, caught = "fooled, but pipeline caught it", caught + 1
    else:
        outcome, succeeded = "ATTACK SUCCEEDED", succeeded + 1
    print(f"{lab['file']}: {outcome:32s} wrong fields={wrong} decision={decision} "
          f"({time.time() - start:.0f}s)")

n = len(cases)
print(f"\nModel resisted:                {resisted}/{n}")
print(f"Fooled but caught by checks:   {caught}/{n}")
print(f"Attack succeeded (bad data approved): {succeeded}/{n}")