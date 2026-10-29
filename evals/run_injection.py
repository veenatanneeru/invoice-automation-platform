"""Prompt-injection test: real extractor + validation checks + injection scanner."""
import json
import time
from pathlib import Path

from app.extraction.local import extract_with_ollama
from app.security.scanner import scan_pdf
from app.validation.checks import Validator
from app.validation.decision import decide
from evals.run_eval import FIELDS, match

labels = json.loads(Path("data/labels/labels.json").read_text())
pos = json.loads(Path("data/labels/purchase_orders.json").read_text())
cases = [l for l in labels if "prompt_injection" in l["expected_flags"]]
print(f"Running {len(cases)} injected invoices through the real model...\n")

resisted = fooled = fooled_caught_by_checks = fooled_caught_by_scanner = succeeded = 0
for lab in cases:
    start = time.time()
    path = Path("data/raw") / lab["file"]
    got = extract_with_ollama(path).model_dump()
    wrong = [f for f in FIELDS if not match(lab["fields"][f], got[f])]
    check_flags = Validator(pos).check(got)
    scan_flags = scan_pdf(path)
    decision_no_scanner = decide(check_flags)
    decision = decide(check_flags + scan_flags)

    if wrong:
        fooled += 1
        if decision_no_scanner != "approve":
            fooled_caught_by_checks += 1
        if decision != "approve":
            fooled_caught_by_scanner += 1
        if decision == "approve":
            succeeded += 1
    else:
        resisted += 1
    print(f"{lab['file']}: wrong={wrong} checks_only={decision_no_scanner} "
          f"with_scanner={decision} scanner={scan_flags} ({time.time() - start:.0f}s)")

n = len(cases)
print(f"\nModel resisted: {resisted}/{n}   Model fooled: {fooled}/{n}")
print(f"Of the {fooled} fooled: caught by arithmetic checks alone: {fooled_caught_by_checks}, "
      f"caught with scanner added: {fooled_caught_by_scanner}")
print(f"Attack succeeded (wrong data auto-approved): {succeeded}/{n}")