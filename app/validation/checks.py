"""Business-rule validation for extracted invoices. Pure Python: no LLM, no cost, deterministic."""

TOL = 0.01


class Validator:
    def __init__(self, purchase_orders):
        self.pos = {p["po_number"]: p for p in purchase_orders}
        self.seen = set()  # (vendor, invoice_number) pairs already processed

    def check(self, f: dict) -> list[str]:
        """Return a list of flag names for one extracted invoice (a dict of the 9 fields)."""
        flags = []
        inv_no, po_no = f.get("invoice_number"), f.get("po_number")
        sub, tax, total = f.get("subtotal"), f.get("tax"), f.get("total")

        if not inv_no:
            flags.append("missing_invoice_number")
        if not po_no:
            flags.append("missing_po")

        if None not in (sub, tax, total) and abs(sub + tax - total) > TOL:
            flags.append("total_mismatch")

        inv_date, due_date = f.get("invoice_date"), f.get("due_date")
        if inv_date and due_date and due_date < inv_date:  # ISO dates compare correctly as text
            flags.append("due_before_invoice")

        if po_no:
            po = self.pos.get(po_no)
            if po is None:
                flags.append("unknown_po")
            else:
                if total is not None and total > po["approved_amount"] + TOL:
                    flags.append("exceeds_po")
                if po["vendor_name"] != f.get("vendor_name"):
                    flags.append("vendor_mismatch")

        if inv_no:
            key = (f.get("vendor_name"), inv_no)
            if key in self.seen:
                flags.append("duplicate")
            self.seen.add(key)

        return flags
