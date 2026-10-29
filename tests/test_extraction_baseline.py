import json

from app.extraction.rules import extract_with_rules
from evals.run_eval import FIELDS, match
from scripts import generate_invoices as gen


def test_rules_baseline_on_generated_easy_set(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "RAW", tmp_path / "raw")
    monkeypatch.setattr(gen, "LABELS", tmp_path / "labels")
    gen.main()
    labels = json.loads((tmp_path / "labels" / "labels.json").read_text())
    ok = total = 0
    for lab in labels[:60]:
        got = extract_with_rules(tmp_path / "raw" / lab["file"]).model_dump()
        for f in FIELDS:
            total += 1
            ok += match(lab["fields"][f], got[f])
    assert ok / total >= 0.99