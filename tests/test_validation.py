from app.validation.checks import Validator
from app.validation.decision import decide

PO = [{"po_number": "PO-1", "vendor_name": "Acme", "approved_amount": 100.0}]


def inv(**kw):
    base = dict(vendor_name="Acme", invoice_number="INV-1", po_number="PO-1",
                invoice_date="2026-01-01", due_date="2026-02-01",
                subtotal=90.0, tax=10.0, total=100.0)
    base.update(kw)
    return base


def test_clean_invoice_has_no_flags():
    assert Validator(PO).check(inv()) == []


def test_total_mismatch():
    assert "total_mismatch" in Validator(PO).check(inv(total=120.0))


def test_exceeds_po():
    flags = Validator(PO).check(inv(subtotal=110.0, tax=0.0, total=110.0))
    assert flags == ["exceeds_po"]


def test_missing_fields():
    flags = Validator(PO).check(inv(invoice_number=None, po_number=None))
    assert "missing_invoice_number" in flags and "missing_po" in flags


def test_unknown_po_and_vendor_mismatch():
    assert "unknown_po" in Validator(PO).check(inv(po_number="PO-999"))
    assert "vendor_mismatch" in Validator(PO).check(inv(vendor_name="Other Co"))


def test_due_before_invoice():
    assert "due_before_invoice" in Validator(PO).check(inv(due_date="2025-12-01"))


def test_duplicate_detected_on_second_submission():
    v = Validator(PO)
    assert v.check(inv()) == []
    assert "duplicate" in v.check(inv())


def test_decisions():
    assert decide([]) == "approve"
    assert decide(["missing_po"]) == "review"
    assert decide(["duplicate", "exceeds_po"]) == "reject"