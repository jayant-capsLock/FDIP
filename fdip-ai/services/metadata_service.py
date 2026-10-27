import re

# ===========================================================================
# Extractors for the 32 additional FDIP document types.
# The public entry point is still extract_metadata(text, document_type);
# the code below is private helper machinery used by its final fallback.
# ===========================================================================

# ---------------------------------------------------------------------------
# COMMON PATTERNS
# ---------------------------------------------------------------------------

# Supports 1,234,567.89  and Indian lakh grouping 12,34,567.89
NUMBER = (
    r"(?:\d{1,2}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d{1,4})?"
)
CURRENCY = r"(?:₹|Rs\.?|INR|＄|\$|€|£)?"
# A captured number must not be the prefix of something longer / a percentage
NUM_END = r"(?!\d|,\d|\.\d|\s*%|[A-Za-z])"

DATE_NC = (
    r"(?:\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}(?:st|nd|rd|th)?[\s\-]+[A-Za-z]{3,9}\.?,?[\s\-]+\d{2,4}"
    r"|[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})"
)
YEAR_NC = (
    r"(?:(?:19|20)\d{2}\s*[-/–]\s*(?:19|20)?\d{2,4}|(?:19|20)\d{2})"
)

GSTIN_NC = r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z][A-Z][0-9A-Z]"
PAN_NC = r"[A-Z]{5}\d{4}[A-Z]"
TAN_NC = r"[A-Z]{4}\d{5}[A-Z]"
VEHICLE_NC = r"[A-Za-z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Za-z]{1,3}[\s\-]?\d{4}"
ID_NC = r"[A-Za-z0-9][A-Za-z0-9_]*(?:[ ]?[-/][ ]?[A-Za-z0-9_]+)*"

STOP = {
    "date", "no", "number", "dated", "of", "for", "the", "to", "from", "id",
    "name", "amount", "total", "due", "tax", "and", "on", "by", "details",
    "as", "at", "in", "is", "ref", "na", "n/a", "nil",
}

# Labels that are too generic to be matched loosely across other words
# ("Total Tax 18.00" must not be read as the total).
_STRICT = {
    "total", "tax", "gst", "vat", "rent", "amount", "balance", "units",
    "fees", "fee", "taxes", "tds", "credits", "debits", "premium",
    "coverage", "idv", "salary", "interest", "dividend", "refund", "cess",
    "pf", "esi", "pt", "deposit", "cash paid", "cash received", "nav",
    "deductions", "withholding", "payments", "purchases", "advance",
    "shipping", "freight", "delivery", "limit", "consumption", "overdue",
}

_TRIM = re.compile(
    r"\s+(?:gstin|gst\s*no|gst\s*number|pan|tan|cin|phone|tel|telephone|"
    r"mobile|email|e-mail|fax|website|challan\s*(?:date|type|no|number)|"
    r"order\s*date|dispatch\s*date|place\s*of\s*supply|ref|date|"
    r"invoice\s*(?:no|number|date)|address|folio|policy\s*(?:no|number)|pin)"
    r"\s*[:\-#]",
    re.IGNORECASE,
)
_LABELISH = re.compile(r"^[A-Za-z][A-Za-z /.#&()]{1,30}:(\s|$)")


# ---------------------------------------------------------------------------
# CONTEXT
# ---------------------------------------------------------------------------

class _Ctx:
    def __init__(self, text):
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\u00a0", " ")
        self.text = "\n".join(
            re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")
        )
        self.lines = [ln for ln in self.text.split("\n") if ln.strip()]
        upper = self.text.upper()
        self.gstins = list(dict.fromkeys(re.findall(r"\b" + GSTIN_NC + r"\b", upper)))
        self.pans = list(dict.fromkeys(re.findall(r"\b" + PAN_NC + r"\b", upper)))
        self.tans = list(dict.fromkeys(re.findall(r"\b" + TAN_NC + r"\b", upper)))


def _clean(v):
    if v is None:
        return None
    v = re.sub(r"\s+", " ", v).strip().strip("[]|:;,_ ").strip()
    return v or None


def _L(label, skip=()):
    """Case-insensitive, whitespace-tolerant label with word boundaries."""
    body = re.escape(label).replace(r"\ ", r"\s*")
    pre = "".join(rf"(?<!{re.escape(w)}\s)" for w in skip)
    return rf"(?i:{pre}\b{body}(?![A-Za-z]))"


def _clean_business_name(candidate):
    """Strip merged street address / phone / email from an OCR'd name."""
    if not candidate:
        return None
    candidate = candidate.strip(" []")
    candidate = re.split(
        r"\s+(?=\d+\s+(?:[A-Za-z][A-Za-z .'-]*\s+)?"
        r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|"
        r"boulevard|blvd\.?|drive|dr\.?))",
        candidate, maxsplit=1, flags=re.IGNORECASE,
    )[0]
    candidate = re.split(
        r"\s+(?=(?:phone|telephone|tel|fax|email|website)\s*[:\-])",
        candidate, maxsplit=1, flags=re.IGNORECASE,
    )[0]
    return candidate.strip(" []") or None


_TOP_IGNORE = re.compile(
    r"\b(?:invoice|receipt|statement|certificate|challan|bill|note|order|"
    r"advice|policy|report|register|book|return|date|gstin|pan|tan|cin|"
    r"phone|tel|telephone|fax|email|website|address|street|road|avenue|"
    r"lane|total|amount|page|original|duplicate|copy|tax|proforma|e-way|"
    r"eway|form|schedule|summary|details|remittance|settlement|delivery)\b",
    re.IGNORECASE,
)


_TITLE_WORDS = re.compile(
    r"\b(?:invoice|tax|receipt|statement|certificate|challan|bill|note|order|"
    r"advice|policy|report|register|book|return|credit|debit|card|loan|account|"
    r"insurance|life|health|electricity|water|gas|payment|purchase|sales|"
    r"proforma|e-way|eway|form|demat|cash|rent|expense|settlement|customer|"
    r"vendor|summary|remittance|original|duplicate|copy|page|delivery)\b",
    re.IGNORECASE,
)


_TOP_IGNORE_HARD = re.compile(
    r"\b(?:gstin|pan|tan|cin|phone|tel|telephone|fax|email|website|address|"
    r"street|road|avenue|lane|total|amount|date|schedule|details)\b",
    re.IGNORECASE,
)


def top_name(ctx, n=8):
    """Best-guess business name from the first lines of the document.
    Label lines ("Foo: bar") are skipped; document-title words are stripped, so
    "HDFC Bank Credit Card Statement" yields "HDFC Bank"."""
    for line in ctx.lines[:n]:
        cand = line.strip(" []")
        if len(cand) < 3 or not re.search(r"[A-Za-z]", cand) or ":" in cand:
            continue
        if re.search(r"\b\d{6}\b|\d[\d,]*\.\d{2}|\d,\d{2,3}", cand):
            continue
        if _TOP_IGNORE_HARD.search(cand):
            continue
        if len(re.findall(r"\d", cand)) > len(re.findall(r"[A-Za-z]", cand)):
            continue
        if _TOP_IGNORE.search(cand):
            cand = re.sub(r"\s+", " ", _TITLE_WORDS.sub(" ", cand)).strip(" -,")
            if (len(cand) < 3 or _TOP_IGNORE.search(cand)
                    or not re.search(r"[A-Za-z]{3}", cand)):
                continue
        return _clean_business_name(cand)
    return None


# ---------------------------------------------------------------------------
# EXTRACTOR BUILDERS
# ---------------------------------------------------------------------------

def lab_val(labels, value, digit=False, post=None, skip=()):
    """label [: -] <value regex>, labels tried in priority order."""
    def fn(ctx):
        for label in labels:
            pat = rf"{_L(label, skip)}[\s.#]*[:\-]?\s*({value})"
            for m in re.finditer(pat, ctx.text):
                v = _clean(m.group(1))
                if not v or v.lower() in STOP:
                    continue
                if digit and not re.search(r"\d", v):
                    continue
                return post(v) if post else v
        return None
    return fn


def ident(*labels):
    return lab_val(labels, ID_NC, digit=True)


def dt(*labels):
    return lab_val(labels, DATE_NC)


def year(*labels):
    return lab_val(labels, YEAR_NC)


def amt(*labels, skip=()):
    def fn(ctx):
        for label in labels:
            L = _L(label, skip)
            nr = r"(?!\s*(?i:rate|percent))"
            pats = [
                # Label: ₹ 1,234.00
                rf"{L}{nr}[\s.#]*[:\-]?\s*{CURRENCY}\s*({NUMBER}){NUM_END}",
                # Label (9%) 90.00   /   Label @ 9% : 90.00
                rf"{L}[\s@(:]*\d+(?:\.\d+)?\s*%[^\d\n]{{0,30}}"
                rf"{CURRENCY}\s*({NUMBER}){NUM_END}",
            ]
            if label.lower() not in _STRICT:
                # OCR noise between label and value
                pats.append(rf"{L}{nr}[^\d%]{{0,40}}{CURRENCY}\s*({NUMBER}){NUM_END}")
            for p in pats:
                m = re.search(p, ctx.text)
                if m:
                    return _clean(m.group(1))
        return None
    return fn


def pct(*labels):
    def fn(ctx):
        for label in labels:
            L = _L(label)
            for p in (
                rf"{L}[\s.#@:\-]*(\d+(?:\.\d+)?)\s*%",
                rf"{L}[^\d\n]{{0,25}}(\d+(?:\.\d+)?)\s*%",
            ):
                m = re.search(p, ctx.text)
                if m:
                    return m.group(1)
        return None
    return fn


def txt(*labels, extra_lines=0):
    """Free-text value after a label on the same line, or on the next line."""
    def fn(ctx):
        for label in labels:
            L = _L(label)
            for pat in (
                rf"{L}[ \t.#]*[:\-][ \t]*([^\n]+)",
                rf"{L}[ \t.#:\-]*\n[ \t]*([^\n]+)",
            ):
                for m in re.finditer(pat, ctx.text):
                    v = _clean(_TRIM.split(" " + m.group(1))[0])
                    if not v:
                        nxt = ctx.text[m.end(1) + 1:].split("\n", 1)[0]
                        v = _clean(_TRIM.split(" " + nxt)[0])
                    if not v or v.lower() in STOP or _LABELISH.match(v):
                        continue
                    if re.fullmatch(rf"(?:{GSTIN_NC}|{PAN_NC}|{TAN_NC})", v.upper()):
                        continue
                    if extra_lines:
                        rest = ctx.text[m.end(1) + 1:].split("\n")
                        for nxt in rest[:extra_lines]:
                            nxt = nxt.strip()
                            if (nxt and ":" not in nxt[:35]
                                    and not re.search(r"\d\.\d{2}\s*$", nxt)):
                                v = f"{v}, {nxt}"
                    return v
        return None
    return fn


def party(labels, top=False):
    base = txt(*labels)

    def fn(ctx):
        v = _clean_business_name(base(ctx)) if base(ctx) else None
        if not v and top:
            v = top_name(ctx)
        return v
    return fn


def _ordered(kind_re, store_attr, idx, labels):
    lv = lab_val(labels, kind_re) if labels else None

    def fn(ctx):
        if lv:
            v = lv(ctx)
            if v:
                return v.upper()
        found = getattr(ctx, store_attr)
        return found[idx] if len(found) > idx else None
    return fn


def gst(idx, *labels):
    return _ordered(GSTIN_NC, "gstins", idx, labels)


def pan(idx, *labels):
    return _ordered(PAN_NC, "pans", idx, labels)


def tan(idx, *labels):
    return _ordered(TAN_NC, "tans", idx, labels)


def keyword(words, fmt=str.title):
    def fn(ctx):
        m = re.search(r"\b(" + "|".join(words) + r")\b", ctx.text, re.IGNORECASE)
        return fmt(m.group(1)) if m else None
    return fn


def first_of(*fns):
    def fn(ctx):
        for f in fns:
            v = f(ctx)
            if v:
                return v
        return None
    return fn


def flag(pattern):
    return lambda ctx: bool(re.search(pattern, ctx.text, re.IGNORECASE))


def currency(ctx):
    t = ctx.text
    if re.search(r"₹|\bRs\.?|\bINR\b", t):
        return "INR"
    if re.search(r"\$|\bUSD\b", t):
        return "USD"
    if re.search(r"€|\bEUR\b", t):
        return "EUR"
    if re.search(r"£|\bGBP\b", t):
        return "GBP"
    return None


def isins(ctx):
    found = list(dict.fromkeys(re.findall(r"\bIN[A-Z0-9]{10}\b", ctx.text.upper())))
    return found or None


def invoice_refs(ctx):
    refs = re.findall(r"\b(INV[-/]?[A-Za-z0-9\-/]*\d[A-Za-z0-9\-/]*)\b", ctx.text, re.I)
    refs += re.findall(
        r"\binvoice\s*(?:no\.?|number|#)\s*[:\-]?\s*(" + ID_NC + r")", ctx.text, re.I
    )
    refs = [r for r in refs if re.search(r"\d", r)]
    return list(dict.fromkeys(refs)) or None


def deductor_tans(ctx):
    return ctx.tans or None


# ---------------------------------------------------------------------------
# TABLE PARSERS (line items / ledger rows)
# ---------------------------------------------------------------------------

_SUMMARY = re.compile(
    r"\b(?:subtotal|sub\s*total|tax|gst|vat|cgst|sgst|igst|cess|total|"
    r"amount\s*due|balance|discount|shipping|freight|round\s*off|"
    r"grand|payable|paid|change)\b",
    re.IGNORECASE,
)
_C = CURRENCY


def items(ctx):
    out = []
    pats = [
        # [sr] Description  qty  unit_price  amount
        (re.compile(
            rf"^\s*(?:\d+\s+)?(.*?[A-Za-z].*?)\s+(\d+(?:\.\d+)?)\s+(?:[A-Za-z]{{2,5}}\s+)?"
            rf"{_C}\s*({NUMBER})\s+{_C}\s*({NUMBER})\s*$"), ("d", "q", "u", "a")),
        # qty  Description  unit_price  amount
        (re.compile(
            rf"^\s*(\d+(?:\.\d+)?)\s+(.*?[A-Za-z].*?)\s+{_C}\s*({NUMBER})\s+{_C}\s*({NUMBER})\s*$"),
         ("q", "d", "u", "a")),
        # qty  Description  amount
        (re.compile(rf"^\s*(\d+(?:\.\d+)?)\s+(.*?[A-Za-z].*?)\s+{_C}\s*({NUMBER})\s*$"),
         ("q", "d", "a")),
        # Description  currency-amount
        (re.compile(
            rf"^\s*(?!\d+\s+)(.*?[A-Za-z].*?)\s+(?:[₹$€£]|Rs\.?|INR)\s*({NUMBER})\s*$"),
         ("d", "a")),
    ]
    for line in ctx.lines:
        if _SUMMARY.search(line) or re.search(r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b", line):
            continue
        for rx, keys in pats:
            m = rx.match(line)
            if m:
                if re.search(r"\b\d{6}\b", line):
                    continue
                if not re.search(r"\d\.\d{2}\b|[₹$€£]|\bRs\b|\bINR\b", line):
                    continue
                rec = {"description": None, "quantity": None,
                       "unit_price": None, "amount": None}
                names = {"d": "description", "q": "quantity",
                         "u": "unit_price", "a": "amount"}
                for k, g in zip(keys, m.groups()):
                    rec[names[k]] = g.strip()
                out.append(rec)
                break
    return out


def deliverables(ctx):
    """Delivery challan lines: description, HSN, quantity (first number after
    the HSN code is the quantity)."""
    out = []
    desc = r"([A-Za-z][A-Za-z &/().,\-]*?[A-Za-z.)])"
    with_hsn = re.compile(rf"^\s*(?:\d{{1,3}}\s+)?{desc}\s+(\d{{4,8}})\s+(\d+(?:\.\d+)?)\b")
    plain = re.compile(
        rf"^\s*(?:\d{{1,3}}\s+)?{desc}\s+(\d{{1,5}}(?:\.\d+)?)\s*"
        r"(?:nos|pcs|units?|kgs?|ltrs?|boxes|box|sets?|mtrs?)?\s*$", re.I)
    for line in ctx.lines:
        if _SUMMARY.search(line) or re.search(r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b", line) or ":" in line:
            continue
        m = with_hsn.match(line)
        if m:
            out.append({"description": m.group(1).strip(), "hsn": m.group(2),
                        "quantity": m.group(3)})
            continue
        m = plain.match(line)
        if m and len(m.group(1)) > 2:
            out.append({"description": m.group(1).strip(), "hsn": None,
                        "quantity": m.group(2)})
    return out


_ROW_DATE = (r"(?:\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
             r"|\d{1,2}[\s\-][A-Za-z]{3}[\s\-]\d{2,4})")


def rows(ledger=True):
    """Dated ledger/transaction rows. 'amount' is the first figure on the row;
    for running-balance ledgers 'balance' is the last."""
    def fn(ctx):
        out = []
        for line in ctx.lines:
            m = re.match(rf"^\s*(?:\d{{1,3}}\s+)?({_ROW_DATE})\b", line)
            if not m:
                continue
            rest = re.sub(_ROW_DATE, " ", line[m.end():])
            amounts = re.findall(r"(?<![\w.])(\d[\d,]*\.\d{2,4})(?!\d)", rest)
            if not amounts:
                continue
            first = re.search(r"(?<![\w.])\d[\d,]*\.\d{2,4}", rest)
            desc = _clean(rest[:first.start()].strip(" -:₹$€£"))
            out.append({
                "date": m.group(1),
                "description": desc,
                "amount": amounts[0],
                "balance": amounts[-1] if ledger and len(amounts) > 1 else None,
                "amounts": amounts,
            })
        return out
    return fn


# ---------------------------------------------------------------------------
# SHARED FIELD GROUPS
# ---------------------------------------------------------------------------

def _tax_block():
    return {
        "taxable_amount": amt("total taxable value", "taxable value",
                              "taxable amount", "total taxable amount"),
        "cgst": amt("cgst", "central tax"),
        "sgst": amt("sgst", "utgst", "state tax"),
        "igst": amt("igst", "integrated tax"),
        "cess": amt("cess"),
        "total_tax": amt("total tax amount", "total tax", "tax amount",
                         "gst amount", "tax due", "sales tax", "gst", "vat", "tax"),
    }


def _gst_return_header():
    return {
        "gstin": gst(0, "gstin of the taxpayer", "gstin/uin", "gstin"),
        "legal_name": txt("legal name of the registered person", "legal name",
                          "trade name", "name of the taxpayer"),
        "return_period": lab_val(
            ("return period", "tax period", "period"),
            r"[A-Za-z]{3,9}\s*[-/]?\s*\d{4}|\d{2}[-/]\d{4}"),
        "financial_year": year("financial year", "f.y.", "fy"),
        "arn": ident("arn"),
        "filing_date": dt("date of filing", "filing date", "filed on"),
    }


_SIG = ("igst", "cgst", "sgst", "cess")

_TOTAL_INV = ("grand total", "total invoice value", "invoice total",
              "total amount due", "total due", "total amount payable",
              "amount payable", "amount due", "balance due", "total amount",
              "total payable", "total")


# ---------------------------------------------------------------------------
# SPECS: document_type -> {field: extractor}
# ---------------------------------------------------------------------------

def col_value(header_pattern):
    """Value under a '#'-style column header: header row and data row are
    consecutive lines with one token per column."""
    def fn(ctx):
        for i, line in enumerate(ctx.lines[:-1]):
            heads = re.findall(r"([A-Za-z][A-Za-z ]*?)\s*#", line)
            if len(heads) < 2:
                continue
            data = ctx.lines[i + 1].split()
            if len(data) != len(heads):
                continue
            for h, d in zip(heads, data):
                if re.search(header_pattern, h, re.I):
                    return d
        return None
    return fn


def _bare_vehicle(ctx):
    """Vehicle plate appearing in a table row with no label next to it."""
    m = re.search(r"\b([A-Z]{2}\d{1,2}[A-Z]{1,3}\d{4})\b", ctx.text.upper().replace("-", ""))
    return m.group(1) if m else None


def _eway_supplier_gstin(ctx):
    labelled = lab_val(("gstin of supplier", "supplier gstin", "from gstin",
                        "consignor gstin"), GSTIN_NC)(ctx)
    if labelled:
        return labelled.upper()
    recipient = lab_val(("gstin of recipient", "recipient gstin", "to gstin",
                         "consignee gstin"), GSTIN_NC)(ctx)
    for g in ctx.gstins:
        if not recipient or g != recipient.upper():
            return g
    return None


SPECS = {}

# ---- Sales / purchase / proforma invoices ---------------------------------

SPECS["sales_invoice"] = {
    "invoice_number": ident("invoice number", "invoice no", "invoice num",
                            "invoice #", "inv no", "bill no", "invoice id"),
    "invoice_date": dt("invoice date", "date of invoice", "dated", "date"),
    "due_date": dt("due date", "payment due", "due on"),
    "seller": party(["seller", "supplier", "sold by", "issued by", "vendor"], top=True),
    "seller_gstin": gst(0, "seller gstin", "supplier gstin", "gstin of supplier"),
    "buyer": party(["buyer", "bill to", "billed to", "customer name", "customer",
                    "sold to", "ship to"]),
    "buyer_gstin": gst(1, "buyer gstin", "customer gstin", "recipient gstin",
                       "gstin of recipient"),
    "place_of_supply": txt("place of supply"),
    "payment_terms": txt("payment terms", "terms of payment"),
    "dispatch_details": txt("dispatch details", "dispatched through", "delivery terms"),
    "items": items,
    "subtotal": amt("subtotal", "sub total", "total before tax"),
    **_tax_block(),
    "total_amount": amt(*_TOTAL_INV),
    "payment_status": first_of(txt("payment status", "status"),
                               keyword(["paid", "unpaid", "overdue"])),
}

SPECS["purchase_invoice"] = {
    "invoice_number": ident("supplier invoice number", "supplier invoice no",
                            "invoice number", "invoice no", "bill no",
                            "vendor invoice number", "invoice #", "invoice id"),
    "invoice_date": dt("invoice date", "bill date", "date of invoice", "date"),
    "due_date": dt("due date", "payment due"),
    "purchase_order_number": ident("purchase order number", "purchase order no",
                                   "po number", "po no", "po #", "po ref"),
    "supplier": party(["supplier name", "supplier", "vendor name", "vendor",
                       "sold by", "issued by", "seller"], top=True),
    "supplier_gstin": gst(0, "supplier gstin", "vendor gstin", "gstin of supplier"),
    "buyer": party(["buyer", "bill to", "billed to", "purchaser", "ship to"]),
    "buyer_gstin": gst(1, "buyer gstin", "recipient gstin", "gstin of recipient"),
    "payment_terms": txt("payment terms", "terms of payment"),
    "items": items,
    "subtotal": amt("subtotal", "sub total", "total before tax"),
    **_tax_block(),
    "input_cgst": amt("input cgst"),
    "input_sgst": amt("input sgst"),
    "total_amount": amt(*_TOTAL_INV),
}

SPECS["proforma_invoice"] = {
    "proforma_number": ident("proforma invoice number", "proforma invoice no",
                             "proforma number", "proforma no", "pi number",
                             "pi no", "quotation number", "quotation no",
                             "quote number", "invoice number", "invoice no"),
    "issue_date": dt("proforma date", "proforma invoice date", "issue date",
                     "quotation date", "invoice date", "date"),
    "valid_until": dt("valid until", "valid till", "valid upto", "validity date",
                      "validity", "expiry date"),
    "seller": party(["seller", "supplier", "vendor", "issued by", "from"], top=True),
    "seller_gstin": gst(0, "seller gstin", "supplier gstin"),
    "buyer": party(["buyer", "bill to", "billed to", "customer name", "customer",
                    "ship to"]),
    "buyer_gstin": gst(1, "buyer gstin", "customer gstin"),
    "payment_terms": txt("payment terms", "terms of payment"),
    "delivery_terms": txt("expected delivery", "delivery terms", "delivery time"),
    "advance_required": amt("advance payment", "advance required", "advance"),
    "bank_details": txt("bank details", "bank name"),
    "items": items,
    "subtotal": amt("subtotal", "sub total"),
    "shipping_charges": amt("shipping charges", "freight charges", "shipping", "freight"),
    **_tax_block(),
    "total_amount": amt(*_TOTAL_INV),
    "is_final_tax_invoice": lambda ctx: not bool(
        re.search(r"not\s+a\s+(?:final\s+)?tax\s+invoice", ctx.text, re.I)),
}

# ---- Credit / debit notes -------------------------------------------------

SPECS["credit_note"] = {
    "credit_note_number": ident("credit note number", "credit note no", "credit note #",
                                "credit memo number", "credit memo no", "cn no",
                                "cn number"),
    "credit_note_date": dt("credit note date", "cn date", "date of issue", "date"),
    "original_invoice_number": ident("original invoice number", "original invoice no",
                                     "against invoice number", "against invoice no",
                                     "reference invoice number", "invoice reference",
                                     "invoice number", "invoice no"),
    "original_invoice_date": dt("original invoice date", "against invoice date",
                                "invoice date"),
    "issuer": party(["issued by", "supplier", "seller", "vendor"], top=True),
    "issuer_gstin": gst(0, "supplier gstin", "seller gstin"),
    "customer": party(["customer name", "customer", "issued to", "bill to",
                       "billed to", "buyer", "recipient", "credited to"]),
    "customer_gstin": gst(1, "customer gstin", "recipient gstin", "buyer gstin"),
    "reason": txt("reason for credit note", "reason for issue", "reason", "remarks",
                  "narration"),
    **_tax_block(),
    "credit_amount": amt("total credit amount", "credit note amount",
                         "total amount credited", "amount credited", "credit amount",
                         "total credit value", "grand total", "total amount", "total"),
}

SPECS["debit_note"] = {
    "debit_note_number": ident("debit note number", "debit note no", "debit note #",
                               "debit memo number", "debit memo no", "dn no",
                               "dn number"),
    "debit_note_date": dt("debit note date", "dn date", "date of issue", "date"),
    "original_invoice_number": ident("original invoice number", "original invoice no",
                                     "against invoice number", "against invoice no",
                                     "reference invoice number", "invoice reference",
                                     "invoice number", "invoice no"),
    "original_invoice_date": dt("original invoice date", "against invoice date",
                                "invoice date"),
    "issued_by": party(["issued by", "buyer", "from"], top=True),
    "issuer_gstin": gst(0, "buyer gstin", "issuer gstin"),
    "supplier": party(["supplier name", "supplier", "vendor name", "vendor",
                       "issued to", "debited to"]),
    "supplier_gstin": gst(1, "supplier gstin", "vendor gstin"),
    "reason": txt("reason for debit note", "reason for issue", "reason", "remarks",
                  "narration"),
    **_tax_block(),
    "debit_amount": amt("total debit amount", "debit note amount", "amount debited",
                        "debit amount", "revised amount payable", "grand total",
                        "total amount", "total"),
}

# ---- Purchase order / delivery challan / e-way bill -----------------------

SPECS["purchase_order"] = {
    "po_number": ident("purchase order number", "purchase order no", "po number",
                       "po no", "po #", "order number", "order no"),
    "po_date": dt("purchase order date", "po date", "order date", "date"),
    "buyer": party(["buyer", "purchaser", "bill to", "billed to", "ordered by"], top=True),
    "buyer_gstin": gst(0, "buyer gstin", "bill to gstin"),
    "supplier": party(["supplier name", "supplier", "vendor name", "vendor", "seller"]),
    "supplier_gstin": gst(1, "supplier gstin", "vendor gstin"),
    "delivery_date": dt("requested delivery date", "expected delivery date",
                        "delivery date", "required by", "delivery by"),
    "shipping_address": txt("shipping address", "ship to", "delivery address",
                            "delivery location", "deliver to", extra_lines=1),
    "payment_terms": txt("payment terms", "terms of payment"),
    "approved_by": txt("approved by", "authorised by", "authorized by"),
    "currency": currency,
    "items": items,
    "subtotal": amt("order subtotal", "subtotal", "sub total"),
    "tax": amt("total tax", "tax amount", "gst amount", "tax", "gst"),
    "total_amount": amt("total order value", "order total", "po total", "grand total",
                        "total amount", "total value", "total"),
}

SPECS["delivery_challan"] = {
    "challan_number": first_of(
        ident("delivery challan number", "delivery challan no", "challan number",
              "challan no", "dc number", "dc no", "delivery challan"),
        col_value(r"challan")),
    "challan_date": dt("challan date", "dc date", "date"),
    "consignor": party(["consignor", "sender", "dispatched from", "dispatch from",
                        "company name"], top=True),
    "consignor_gstin": gst(0, "consignor gstin", "sender gstin"),
    "consignee": party(["consignee", "receiver", "delivered to", "ship to", "bill to"]),
    "consignee_gstin": gst(1, "consignee gstin", "receiver gstin"),
    "purchase_order_number": ident("purchase order number", "purchase order no",
                                   "po number", "po no", "po ref", "order no",
                                   "ref"),
    "dispatch_date": first_of(dt("dispatch date", "date of dispatch", "dispatched on"),
                              col_value(r"dispatch")),
    "vehicle_number": lab_val(("vehicle number", "vehicle no", "vehicle", "truck no"),
                              VEHICLE_NC, post=lambda v: re.sub(r"[\s\-]", "", v).upper()),
    "transporter": txt("transporter name", "transporter", "carrier"),
    "lr_number": ident("lr number", "lr no", "lorry receipt no", "gr no"),
    "delivery_location": txt("delivery location", "delivery address",
                             "place of delivery", "deliver to", extra_lines=1),
    "received_by": txt("received by", "receiver name"),
    "items": deliverables,
}

SPECS["eway_bill"] = {
    "eway_bill_number": lab_val(
        ("e-way bill number", "eway bill number", "e-way bill no", "eway bill no",
         "ewb no", "ewb number", "e-way bill"),
        r"\d{4}\s?\d{4}\s?\d{4}", post=lambda v: re.sub(r"\s", "", v)),
    "generated_date": dt("generated date", "e-way bill date", "eway bill date",
                         "generated on", "date"),
    "valid_until": dt("valid until", "valid upto", "valid till", "valid to",
                      "validity"),
    "supplier_gstin": lambda ctx: _eway_supplier_gstin(ctx),
    "recipient_gstin": gst(1, "gstin of recipient", "recipient gstin", "to gstin",
                           "consignee gstin"),
    "supplier_name": txt("supplier name", "consignor", "supplier"),
    "recipient_name": txt("recipient name", "consignee", "recipient", "bill to"),
    "document_number": ident("document number", "document no",
                             "invoice /challan no", "invoice/challan no",
                             "invoice number", "invoice no", "challan number"),
    "document_date": dt("document date", "invoice /challan date",
                        "invoice/challan date", "invoice date"),
    "place_of_dispatch": txt("place of dispatch", "dispatch from", "from place"),
    "place_of_delivery": txt("place of delivery", "delivery destination", "to place"),
    "vehicle_number": first_of(
        lab_val(("vehicle number", "vehicle no", "vehicle"), VEHICLE_NC,
                post=lambda v: re.sub(r"[\s\-]", "", v).upper()),
        lambda ctx: _bare_vehicle(ctx)),
    "transporter_id": lab_val(("transporter id", "transporter gstin", "transin"),
                              r"[0-9A-Z]{15}|\d{6,}"),
    "transporter_name": txt("transporter name", "transporter"),
    "transport_mode": txt("transport mode", "transportation mode", "mode"),
    "distance_km": lab_val(("approximate distance", "approx distance", "distance"),
                           r"\d{1,5}"),
    "hsn_code": lab_val(("hsn code", "hsn"), r"\d{2,8}"),
    "goods_value": amt("total invoice value", "goods value", "value of goods",
                       "taxable value", "total value"),
}

# ---- Payment advice / settlement / statements -----------------------------

SPECS["payment_advice"] = {
    "advice_number": ident("payment advice number", "payment advice no",
                           "remittance advice number", "remittance advice no",
                           "advice number", "advice no", "advice #",
                           "remittance number"),
    "advice_date": dt("advice date", "remittance date", "date of advice", "date"),
    "payment_date": dt("payment date", "date of payment", "value date", "paid on",
                       "transfer date", "transaction date"),
    "payer": txt("payer name", "payer", "paid by", "remitter", "customer name"),
    "payee": txt("payee name", "payee", "beneficiary name", "beneficiary", "paid to",
                 "supplier name", "vendor name", "supplier", "vendor"),
    "utr": ident("utr number", "utr no", "utr", "transaction id",
                 "transaction reference", "bank reference number", "reference no",
                 "reference number"),
    "payment_mode": txt("payment mode", "mode of payment", "payment method"),
    "bank_name": txt("bank name", "bank"),
    "bank_account": lab_val(("beneficiary account number", "account number",
                             "account no", "a/c no"), r"[0-9Xx*][0-9Xx*\- ]{3,}"),
    "invoice_references": invoice_refs,
    "gross_amount": amt("gross amount", "total invoice amount", "total invoiced",
                        "gross payment"),
    "total_deductions": amt("total deductions", "tds deducted", "withholding tax",
                            "withholding", "tds", "deductions"),
    "total_amount": amt("total remitted amount", "total amount remitted",
                        "net amount paid", "net payment amount", "total remitted",
                        "net amount", "payment amount", "amount paid", "net payment",
                        "total amount"),
}

SPECS["settlement_report"] = {
    "settlement_id": ident("settlement id", "settlement number", "settlement no",
                           "settlement reference", "payout id"),
    "settlement_date": dt("settlement date", "payout date", "date of settlement",
                          "settled on"),
    "gateway": keyword(["razorpay", "payu", "cashfree", "paytm", "stripe",
                        "ccavenue", "billdesk", "phonepe", "instamojo"]),
    "merchant": txt("merchant name", "merchant", "business name", "account name"),
    "merchant_id": ident("merchant id", "mid"),
    "settlement_period": txt("settlement period", "period"),
    "transaction_count": lab_val(("total transactions", "transaction count",
                                  "number of transactions", "no of transactions"),
                                 r"\d{1,9}"),
    "gross_amount": amt("gross amount", "gross sales", "gross collections",
                        "total gross", "total sales", "gross settlement"),
    "fees": amt("total fees", "gateway fees", "transaction fees", "gateway commission",
                "commission", "mdr", "fees"),
    "gst_on_fees": amt("gst on fees", "gst on commission", "service tax", "taxes"),
    "refunds": amt("total refunds", "refund amount", "refunds"),
    "chargebacks": amt("chargeback amount", "chargebacks", "chargeback"),
    "net_settlement": amt("net settlement amount", "net payout", "net settlement",
                          "net amount settled", "settlement amount", "amount settled",
                          "net amount"),
    "utr": ident("utr number", "utr no", "bank utr", "utr", "bank reference number"),
    "bank_account": txt("settlement account", "settled to", "bank account"),
}

SPECS["customer_statement"] = {
    "customer_name": txt("customer name", "account name", "party name", "bill to",
                         "customer"),
    "account_code": ident("customer code", "customer id", "account code",
                          "account number", "account no", "party code"),
    "issued_by": lambda ctx: top_name(ctx),
    "statement_period": txt("statement period", "for the period", "period"),
    "statement_date": dt("statement date", "as on", "date"),
    "opening_balance": amt("opening balance", "balance brought forward",
                           "brought forward"),
    "total_debits": amt("total invoiced", "total debits", "total debit",
                        "total invoices"),
    "total_credits": amt("total receipts", "total credits", "total credit",
                         "total payments received", "total payments"),
    "overdue_amount": amt("total overdue", "overdue amount", "overdue"),
    "closing_balance": amt("closing balance", "total outstanding",
                           "outstanding balance", "balance due", "amount due",
                           "total due", "closing outstanding"),
    "transactions": rows(True),
}

SPECS["vendor_statement"] = {
    "vendor_name": txt("vendor name", "supplier name", "vendor", "supplier"),
    "account_number": ident("vendor code", "vendor id", "account number",
                            "account no", "supplier code"),
    "buyer": lambda ctx: top_name(ctx),
    "statement_period": txt("statement period", "for the period", "period"),
    "statement_date": dt("statement date", "as on", "date"),
    "opening_balance": amt("opening balance", "balance brought forward",
                           "brought forward"),
    "total_debits": amt("total debits", "total debit", "total payments",
                        "total paid"),
    "total_credits": amt("total credits", "total credit", "total invoiced",
                         "total bills"),
    "overdue_amount": amt("total overdue", "overdue amount", "overdue"),
    "closing_balance": amt("closing balance", "outstanding payable",
                           "balance payable", "total outstanding", "balance due",
                           "amount due", "total due"),
    "transactions": rows(True),
}

SPECS["cash_book"] = {
    "business_name": first_of(txt("business name", "company name", "firm name"),
                              lambda ctx: top_name(ctx)),
    "period": txt("for the period", "cash book for", "period", "month"),
    "opening_balance": amt("opening cash balance", "opening balance", "opening cash",
                           "balance b/f", "balance brought forward", "brought forward"),
    "closing_balance": amt("closing cash balance", "closing balance", "closing cash",
                           "balance c/d", "balance carried forward", "carried forward"),
    "total_receipts": amt("total cash receipts", "total receipts", "total receipt",
                          "total cash received", "total debit"),
    "total_payments": amt("total cash payments", "total payments", "total payment",
                          "total cash paid", "total credit"),
    "cash_deposited_to_bank": amt("cash deposited into bank", "cash deposited",
                                  "deposited in bank"),
    "cash_withdrawn": amt("cash withdrawn", "withdrawn from bank"),
    "transactions": rows(True),
}

# ---- Banking / investments / insurance ------------------------------------

SPECS["loan_statement"] = {
    "loan_account_number": ident("loan account number", "loan account no",
                                 "loan a/c no", "loan number", "loan no",
                                 "account number", "account no"),
    "borrower": txt("borrower name", "borrower", "customer name", "applicant name",
                    "name"),
    "lender": first_of(txt("lender", "bank name", "financial institution", "nbfc"),
                       lambda ctx: top_name(ctx)),
    "statement_date": dt("statement date", "as on date", "as on", "date"),
    "statement_period": txt("statement period", "period"),
    "sanctioned_amount": amt("sanctioned loan amount", "sanctioned amount",
                             "loan amount sanctioned", "sanction amount",
                             "loan amount", "disbursed amount"),
    "interest_rate": pct("rate of interest", "interest rate", "roi", "interest"),
    "tenure": txt("loan tenure", "tenure", "tenor"),
    "emi_amount": amt("emi amount", "installment amount", "instalment amount",
                      "monthly installment", "emi"),
    "next_due_date": dt("next due date", "emi due date", "installment due date",
                        "due date"),
    "maturity_date": dt("maturity date", "loan end date", "last emi date"),
    "opening_principal": amt("opening principal", "opening balance"),
    "closing_principal": amt("closing principal", "closing balance"),
    "principal_outstanding": amt("principal outstanding", "outstanding principal",
                                 "principal balance", "loan outstanding",
                                 "outstanding amount", "outstanding balance"),
    "interest_outstanding": amt("interest outstanding", "outstanding interest"),
    "overdue_amount": amt("total overdue", "overdue amount", "amount overdue", "overdue"),
    "penal_interest": amt("penal interest", "penalty interest", "penal charges",
                          "late payment charges"),
    "foreclosure_charges": amt("foreclosure charges", "foreclosure charge",
                               "prepayment charges"),
    "transactions": rows(True),
}

SPECS["credit_card_statement"] = {
    "card_number": lab_val(("credit card number", "card account number",
                            "card number", "card no", "card #"),
                           r"[Xx*•\d][Xx*•\d \-]{7,}", post=lambda v: v.strip()),
    "cardholder": txt("cardholder name", "card holder name", "card member name",
                      "cardholder", "customer name", "name"),
    "issuer": first_of(txt("issuer", "bank name", "bank"), lambda ctx: top_name(ctx)),
    "statement_date": dt("statement date", "statement generation date",
                         "date of statement"),
    "statement_period": txt("statement period", "billing period", "billing cycle"),
    "payment_due_date": dt("payment due date", "due date", "pay by"),
    "credit_limit": amt("total credit limit", "credit limit"),
    "available_credit": amt("available credit limit", "available credit",
                            "available limit"),
    "previous_balance": amt("previous statement balance", "previous balance",
                            "opening balance"),
    "payments_received": amt("payments and credits", "payments received",
                             "payment received", "payments/credits", "payments",
                             "credits"),
    "purchases": amt("purchases and debits", "purchases/debits", "new purchases",
                     "purchases"),
    "finance_charges": amt("finance charges", "finance charge", "interest charges",
                           "interest charged"),
    "late_payment_fee": amt("late payment fee", "late fee"),
    "closing_balance": amt("closing balance", "new balance", "statement balance",
                           "current balance"),
    "total_amount_due": amt("total amount due", "total dues", "total due",
                            "amount due"),
    "minimum_amount_due": amt("minimum amount due", "minimum payment due",
                              "minimum due", "min amount due", "min due"),
    "transactions": rows(False),
}

SPECS["demat_statement"] = {
    "bo_id": lab_val(("bo id", "beneficiary owner id", "beneficiary id",
                      "demat account number"), r"[A-Za-z0-9]{8,16}", digit=True),
    "dp_id": lab_val(("dp id", "depository participant id"), r"[A-Za-z0-9]{6,8}",
                     digit=True),
    "client_id": ident("client id", "client id no"),
    "depository": keyword(["nsdl", "cdsl"], fmt=str.upper),
    "dp_name": txt("dp name", "depository participant", "participant name"),
    "account_holder": txt("first holder", "name of the first holder", "account holder",
                         "holder name", "investor name", "name"),
    "pan": pan(0, "pan"),
    "statement_period": txt("statement period", "period"),
    "statement_date": dt("statement date", "as on"),
    "opening_balance": amt("opening balance", "opening holding value", "opening value"),
    "closing_balance": amt("closing balance", "closing holding value",
                           "total portfolio value", "total holding value",
                           "portfolio value", "closing value"),
    "isins": isins,
    "transactions": rows(True),
}

SPECS["mutual_fund_statement"] = {
    "folio_number": lab_val(("folio number", "folio no", "folio"),
                            r"[0-9A-Za-z/]{4,20}", digit=True),
    "investor_name": txt("investor name", "first holder", "unit holder",
                         "name of investor", "investor", "name"),
    "investor_pan": pan(0, "pan"),
    "amc": txt("amc", "fund house", "asset management company", "mutual fund"),
    "scheme_name": txt("scheme name", "scheme"),
    "isin": lambda ctx: (isins(ctx) or [None])[0],
    "statement_period": txt("statement period", "period"),
    "units": amt("closing unit balance", "total units", "unit balance",
                 "balance units", "units"),
    "nav": amt("nav per unit", "current nav", "nav as on", "nav"),
    "cost_value": amt("cost value", "total investment", "amount invested",
                      "invested amount", "purchase value", "cost of investment"),
    "current_value": amt("current value", "market value", "closing value",
                         "present value", "valuation"),
    "transactions": rows(False),
}

SPECS["insurance_policy"] = {
    "policy_number": ident("policy number", "policy no", "policy #",
                           "certificate number"),
    "policyholder": txt("policyholder name", "policy holder name", "policyholder",
                        "policy holder", "name of the insured", "insured name",
                        "proposer name", "insured"),
    "insurer": first_of(txt("insurer", "insurance company", "underwriter",
                            "issued by", "company name"),
                        lambda ctx: top_name(ctx)),
    "insurance_type": keyword(["life", "health", "motor", "vehicle", "travel",
                               "home", "fire", "general"]),
    "policy_start_date": dt("policy start date", "start date", "commencement date",
                            "date of commencement", "risk commencement date",
                            "inception date", "effective date"),
    "maturity_date": dt("maturity date", "policy end date", "end date",
                        "expiry date", "date of expiry", "valid till", "valid upto"),
    "policy_term": txt("policy term", "policy period", "tenure"),
    "sum_insured": amt("sum insured", "sum assured", "coverage amount",
                       "cover amount", "insured amount", "idv", "coverage"),
    "premium_amount": amt("total premium payable", "premium amount", "total premium",
                          "annual premium", "premium payable", "premium"),
    "premium_frequency": txt("premium payment frequency", "payment frequency",
                             "premium frequency"),
    "premium_due_date": dt("premium due date", "next due date", "renewal date",
                           "due date"),
    "nominee": txt("nominee name", "nominee", "beneficiary"),
    "policy_status": txt("policy status", "status"),
}

# ---- Payroll / HR / expenses ----------------------------------------------

SPECS["payroll_register"] = {
    "company": first_of(txt("company name", "employer", "organization",
                            "organisation"), lambda ctx: top_name(ctx)),
    "pay_period": txt("pay period", "payroll month", "for the month of", "month",
                      "period"),
    "department": txt("department"),
    "employee_count": lab_val(("total employees", "number of employees",
                               "no of employees", "employee count", "headcount",
                               "employees"), r"\d{1,6}"),
    "total_gross_salary": amt("total gross salary", "total gross earnings",
                              "total gross", "total earnings", "gross salary"),
    "total_deductions": amt("total deductions"),
    "total_net_salary": amt("total net salary", "total net pay", "total net payable",
                            "net salary payable", "total net", "net salary", "net pay"),
    "total_pf": amt("total pf", "pf employer contribution", "provident fund", "pf"),
    "total_esi": amt("total esi", "employee state insurance", "esi"),
    "total_tds": amt("total tds", "income tax", "tds"),
    "total_professional_tax": amt("professional tax", "pt"),
    "payment_date": dt("bank transfer date", "disbursement date", "payment date",
                       "pay date"),
}

SPECS["reimbursement_claim"] = {
    "claim_number": ident("claim number", "claim no", "claim id",
                          "reimbursement number", "request number", "request no"),
    "employee_name": txt("employee name", "claimant name", "claimant", "employee",
                         "name"),
    "employee_id": ident("employee id", "employee number", "emp id", "emp no",
                         "employee code", "emp code"),
    "department": txt("department"),
    "claim_date": dt("claim date", "date of claim", "submitted date",
                     "date submitted", "submission date", "date"),
    "claim_type": txt("claim type", "type of claim", "expense type",
                      "claim category", "category"),
    "expense_description": txt("expense description", "description", "purpose"),
    "claimed_amount": amt("total claimed amount", "claimed amount", "claim amount",
                          "total amount claimed", "amount claimed", "total claim",
                          "total"),
    "approved_amount": amt("approved amount", "amount approved", "total approved"),
    "approval_status": txt("approval status", "claim status", "status"),
    "approved_by": txt("approved by", "approver", "manager name", "manager"),
    "payment_reference": ident("payment reference", "payment ref", "utr",
                               "transaction id"),
    "reimbursement_date": dt("reimbursement date", "payment date", "date of payment",
                             "paid on", "paid date"),
    "currency": currency,
}

SPECS["expense_report"] = {
    "report_number": ident("expense report number", "expense report no",
                           "report number", "report no", "report id", "report #"),
    "employee_name": txt("employee name", "submitted by", "employee", "name"),
    "employee_id": ident("employee id", "employee number", "emp id", "employee code"),
    "department": txt("department"),
    "reporting_period": txt("reporting period", "report period", "expense period",
                            "period"),
    "submitted_date": dt("submitted date", "date submitted", "submission date",
                         "report date", "date"),
    "business_purpose": txt("business purpose", "trip purpose", "purpose of expense",
                            "purpose"),
    "cost_centre": txt("cost centre", "cost center"),
    "project_code": txt("project code", "project id", "project"),
    "total_claimed": amt("total claimed amount", "total claimed", "total expenses",
                         "total expense", "total amount claimed", "total amount",
                         "total"),
    "approved_amount": amt("approved amount", "total approved", "amount approved"),
    "policy_limit": amt("policy limit", "limit"),
    "approval_status": txt("approval status", "status"),
    "currency": currency,
    "expenses": rows(False),
}

# ---- Utilities / rent -----------------------------------------------------

SPECS["utility_bill"] = {
    "provider": first_of(txt("service provider", "utility provider", "provider",
                             "company"), lambda ctx: top_name(ctx)),
    "utility_type": keyword(["electricity", "water", "gas", "broadband", "internet",
                             "telephone", "mobile", "dth"]),
    "consumer_name": txt("consumer name", "customer name", "name"),
    "consumer_number": ident("consumer number", "consumer no", "consumer id",
                             "service connection number", "connection number",
                             "customer id", "ca number", "account number",
                             "account no"),
    "bill_number": ident("bill number", "bill no", "invoice number", "bill id"),
    "bill_date": dt("bill date", "bill issue date", "date of issue", "issue date",
                    "bill generated on", "date"),
    "due_date": dt("due date", "last date of payment", "payment due date", "pay by"),
    "billing_period": txt("billing period", "bill period", "billing cycle", "period"),
    "previous_reading": lab_val(("previous reading", "opening reading", "old reading",
                                 "prev reading"), NUMBER),
    "current_reading": lab_val(("current reading", "closing reading", "new reading",
                                "present reading"), NUMBER),
    "units_consumed": amt("units consumed", "total units", "units billed", "net units",
                          "consumption"),
    "tariff": txt("tariff category", "tariff"),
    "fixed_charges": amt("fixed charges", "fixed charge"),
    "usage_charges": amt("energy charges", "usage charges", "consumption charges",
                         "variable charges"),
    "taxes": amt("electricity duty", "taxes"),
    "late_payment_surcharge": amt("late payment surcharge", "delayed payment charges",
                                  "late fee", "surcharge"),
    "total_amount_payable": amt("total amount payable", "net amount payable",
                                "net payable amount", "amount payable",
                                "total payable", "total bill amount",
                                "total amount due", "amount due", "total"),
    "payment_status": first_of(txt("payment status", "status"),
                               keyword(["paid", "unpaid", "overdue"])),
}

SPECS["rent_receipt"] = {
    "receipt_number": ident("receipt number", "receipt no", "receipt #"),
    "receipt_date": dt("receipt date", "date of receipt", "date"),
    "landlord_name": txt("name of landlord", "landlord name", "landlord", "owner name",
                         "received by"),
    "landlord_pan": pan(0, "landlord pan", "pan of landlord", "owner pan", "pan"),
    "tenant_name": txt("name of tenant", "tenant name", "tenant", "received from"),
    "property_address": txt("property address", "rented premises",
                            "address of property", "rental property address",
                            "premises", "address", extra_lines=1),
    "rental_period": txt("rental period", "rent period", "rent for the month of",
                         "for the month of", "period", "month"),
    "rent_amount": amt("rent amount", "monthly rent", "rent paid", "rent received",
                       "amount received", "rent", "amount"),
    "security_deposit": amt("security deposit", "deposit"),
    "payment_mode": txt("payment mode", "mode of payment", "payment method", "paid by"),
    "transaction_id": ident("transaction id", "transaction no", "transaction reference",
                            "utr", "cheque number", "cheque no"),
    "landlord_signature_present": flag(r"signature|signed"),
}

# ---- Tax / statutory ------------------------------------------------------

SPECS["form16"] = {
    "certificate_number": ident("certificate number", "certificate no"),
    "employer_name": txt("name of the employer", "name of employer", "employer name",
                         "employer", "name and address of the employer"),
    "employer_tan": tan(0, "tan of the deductor", "employer tan", "tan"),
    "employer_pan": pan(0, "pan of the deductor", "employer pan"),
    "employee_name": txt("name of the employee", "name of employee", "employee name",
                         "employee"),
    "employee_pan": pan(1, "pan of the employee", "employee pan"),
    "financial_year": year("financial year", "f.y.", "fy"),
    "assessment_year": year("assessment year", "a.y.", "ay"),
    "gross_salary": amt("gross salary", "total gross salary"),
    "exempt_allowances": amt("exempt allowances", "allowances to the extent exempt"),
    "total_deductions": amt("aggregate of deductible amount under chapter vi-a",
                            "deductions under chapter vi-a", "total deductions"),
    "taxable_income": amt("total taxable income", "taxable income",
                          "income chargeable under the head salaries"),
    "tax_deducted": amt("total tax deducted", "tax deducted", "total tds",
                        "tax payable"),
    "tax_deposited": amt("tax deposited", "amount deposited"),
}

SPECS["tds_certificate"] = {
    "certificate_number": ident("certificate number", "certificate no"),
    "deductor_name": txt("name of the deductor", "name of deductor", "deductor name",
                         "deductor"),
    "deductor_tan": tan(0, "tan of the deductor", "deductor tan", "tan"),
    "deductee_name": txt("name of the deductee", "name of deductee", "deductee name",
                         "deductee"),
    "deductee_pan": pan(0, "pan of the deductee", "deductee pan", "pan"),
    "quarter": lab_val(("quarter",), r"Q\s*[1-4]|[1-4](?:st|nd|rd|th)?"),
    "financial_year": year("financial year", "f.y.", "fy"),
    "assessment_year": year("assessment year", "a.y.", "ay"),
    "section": lab_val(("under section", "section"), r"\d{3}[A-Z]{0,2}"),
    "amount_paid": amt("amount paid/credited", "amount paid", "amount credited",
                       "total amount paid"),
    "tax_deducted": amt("amount of tax deducted", "total tax deducted", "tax deducted",
                        "tds amount"),
    "tax_deposited": amt("tax deposited", "amount deposited"),
    "date_of_deduction": dt("date of deduction", "date of payment/credit",
                            "date of credit"),
    "deposit_date": dt("date of deposit", "deposit date"),
    "challan_number": ident("challan identification number", "challan no", "cin"),
}

SPECS["form26as"] = {
    "pan": pan(0, "permanent account number", "pan"),
    "name": txt("name of assessee", "assessee name", "assessee", "name"),
    "assessment_year": year("assessment year", "a.y.", "ay"),
    "financial_year": year("financial year", "f.y.", "fy"),
    "deductor_tans": deductor_tans,
    "total_tds": amt("total amount of tax deducted", "total tax deducted",
                     "total tds deducted", "total tds"),
    "advance_tax": amt("total advance tax", "advance tax"),
    "self_assessment_tax": amt("self assessment tax", "self-assessment tax"),
    "refund_amount": amt("total refund", "refund"),
    "challan_serial": ident("challan serial number", "serial number", "bsr code"),
}

SPECS["ais_tis"] = {
    "pan": pan(0, "permanent account number", "pan"),
    "name": txt("name of assessee", "taxpayer name", "assessee", "name"),
    "financial_year": year("financial year", "f.y.", "fy"),
    "assessment_year": year("assessment year", "a.y.", "ay"),
    "document_variant": lambda ctx: (
        "AIS" if re.search(r"annual information statement|\bais\b", ctx.text, re.I)
        else ("TIS" if re.search(r"taxpayer information summary|\btis\b", ctx.text, re.I)
              else None)),
    "salary_income": amt("salary income", "salary"),
    "interest_income": amt("interest income", "interest from savings",
                           "interest"),
    "dividend_income": amt("dividend income", "dividend"),
    "tds_tcs": amt("total tds/tcs", "total tds", "tds/tcs", "tds"),
}

SPECS["itr"] = {
    "itr_form": lambda ctx: (
        "ITR-" + m.group(1).upper()
        if (m := re.search(r"\bITR[\s\-]*([1-7]|U)\b", ctx.text, re.I)) else None),
    "pan": pan(0, "permanent account number", "pan"),
    "name": txt("name of assessee", "assessee name", "name"),
    "assessment_year": year("assessment year", "a.y.", "ay"),
    "financial_year": year("financial year", "previous year", "f.y."),
    "acknowledgement_number": lab_val(
        ("acknowledgement number", "acknowledgment number", "acknowledgement no",
         "ack number", "ack no"), r"\d{6,}"),
    "filing_date": dt("date of filing", "filing date", "filed on", "e-filing date"),
    "gross_total_income": amt("gross total income"),
    "total_deductions": amt("deductions under chapter vi-a", "total deductions",
                            "deductions"),
    "total_income": amt("total income", "taxable income", skip=("gross",)),
    "tax_liability": amt("total tax liability", "net tax liability", "tax liability",
                         "total tax payable", "tax payable"),
    "taxes_paid": amt("total taxes paid", "taxes paid", "total tax paid", "tax paid"),
    "balance_tax_payable": amt("balance tax payable", "net tax payable"),
    "refund_amount": amt("refund due", "refund amount", "refund"),
}

SPECS["gstr1"] = {
    **_gst_return_header(),
    "total_taxable_value": amt("total taxable value", "taxable value",
                               "taxable turnover"),
    "total_invoice_value": amt("total invoice value"),
    "igst": amt("integrated tax", "igst"),
    "cgst": amt("central tax", "cgst"),
    "sgst": amt("state/ut tax", "state tax", "sgst"),
    "cess": amt("cess"),
    "total_tax_liability": amt("total tax liability", "total tax"),
}

SPECS["gstr3b"] = {
    **_gst_return_header(),
    "outward_taxable_value": amt("outward taxable supplies", "total taxable value",
                                 "taxable value"),
    "igst": amt("integrated tax", "igst"),
    "cgst": amt("central tax", "cgst"),
    "sgst": amt("state/ut tax", "state tax", "sgst"),
    "cess": amt("cess"),
    "itc_claimed": amt("net itc available", "total itc available", "itc available",
                       "eligible itc", "itc claimed", "input tax credit"),
    "itc_reversed": amt("itc reversed", "itc reversal", "ineligible itc"),
    "net_tax_payable": amt("net tax payable", "total tax payable", "tax payable"),
    "tax_paid_in_cash": amt("tax paid in cash", "paid through cash", "cash tax paid",
                            "tax paid through cash ledger"),
    "interest": amt("interest payable", "interest"),
    "late_fee": amt("late fee"),
}

SPECS["gstr2b"] = {
    "gstin": gst(0, "gstin of the recipient", "gstin"),
    "legal_name": txt("legal name", "trade name"),
    "return_period": lab_val(("return period", "tax period", "period"),
                             r"[A-Za-z]{3,9}\s*[-/]?\s*\d{4}|\d{2}[-/]\d{4}"),
    "financial_year": year("financial year", "f.y.", "fy"),
    "generated_date": dt("date of generation", "generation date", "generated on"),
    "itc_available": amt("total itc available", "itc available",
                         "total input tax credit"),
    "itc_not_available": amt("total itc not available", "itc not available"),
    "itc_reversal": amt("itc reversal", "itc reversed"),
    "igst": amt("integrated tax", "igst"),
    "cgst": amt("central tax", "cgst"),
    "sgst": amt("state/ut tax", "state tax", "sgst"),
    "cess": amt("cess"),
}

SPECS["gst_payment_challan"] = {
    "cpin": ident("cpin"),
    "cin": ident("cin"),
    "gstin": gst(0, "gstin"),
    "taxpayer_name": txt("legal name", "name of taxpayer", "name"),
    "challan_date": dt("challan generated date", "challan creation date",
                       "challan date", "date of creation", "created on"),
    "payment_date": dt("payment date", "date of payment", "paid on", "deposited on"),
    "payment_mode": txt("mode of payment", "payment mode"),
    "bank": txt("bank name", "bank"),
    "bank_reference": ident("bank reference number", "bank reference no",
                            "bank ref no", "bank transaction reference", "brn",
                            "utr"),
    "payment_status": txt("payment status", "status"),
    "igst": amt("integrated tax", "igst"),
    "cgst": amt("central tax", "cgst"),
    "sgst": amt("state/ut tax", "state tax", "sgst"),
    "cess": amt("cess"),
    "interest": amt("interest"),
    "penalty": amt("penalty"),
    "total_amount": amt("total challan amount", "amount deposited", "total amount",
                        "total"),
}


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

_EXTENDED_DOCUMENT_TYPES = frozenset(SPECS)


def _extract_extended_metadata(text, document_type):
    """Return {field: value} for any of the 32 extended document types,
    or None if document_type is not handled here."""
    spec = SPECS.get(document_type)
    if spec is None:
        return None
    ctx = _Ctx(text)
    result = {}
    for field, fn in spec.items():
        try:
            result[field] = fn(ctx)
        except Exception:  # one bad pattern must never fail the whole document
            result[field] = None
    return result


def extract_metadata(text, document_type):

    text = text or ""

    # ---------------------------------------------------------
    # OCR NORMALIZATION
    # ---------------------------------------------------------

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    search_text = re.sub(r"[ \t]+", " ", text).strip()

    # ---------------------------------------------------------
    # COMMON REGEX COMPONENTS
    # ---------------------------------------------------------

    NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"

    CURRENCY = r"(?:₹|Rs\.?|INR|＄|\$|€|£)?"

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    def clean_value(value):

        if value is None:
            return None

        value = re.sub(r"\s+", " ", value).strip()
        value = value.strip("[] ")

        return value if value else None

    def first_match(patterns, source=search_text):

        for pattern in patterns:

            match = re.search(
                pattern,
                source,
                re.IGNORECASE
            )

            if match:
                return clean_value(match.group(1))

        return None

    document_lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # ---------------------------------------------------------
    # VENDOR / MERCHANT CLEANING
    # ---------------------------------------------------------

    def clean_business_name(candidate):

        if not candidate:
            return None

        candidate = candidate.strip(" []")

        # OCR may merge company name + street address.
        candidate = re.split(
            r"\s+(?=\d+\s+(?:[A-Za-z][A-Za-z .'-]*\s+)?"
            r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|"
            r"lane|ln\.?|boulevard|blvd\.?|drive|dr\.?))",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0]

        # OCR may merge company name + phone/email.
        candidate = re.split(
            r"\s+(?=(?:phone|telephone|tel|fax|email|website)"
            r"\s*[:\-]?)",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0]

        return candidate.strip(" []") or None

    # =========================================================
    # INVOICE
    # =========================================================

    if document_type == "invoice":

        # -----------------------------------------------------
        # INVOICE NUMBER
        # -----------------------------------------------------

        invoice_number = first_match([
            r"\binvoice\s*(?:number|num(?:ber)?|no\.?|#|h)"
            r"\s*[:\-]?\s*[\[\(]?\s*"
            r"([A-Za-z0-9][A-Za-z0-9\-_\/]*)",

            r"\binvoiceh\s*[:\-]?\s*[\[\(]?\s*"
            r"([A-Za-z0-9][A-Za-z0-9\-_\/]*)",
        ])

        # Reject obvious OCR false positives.
        if invoice_number:

            if invoice_number.upper() in {
                "INVOICE",
                "DATE",
                "NO",
                "NUMBER",
                "H",
                "ON"
            }:
                invoice_number = None

        # -----------------------------------------------------
        # VENDOR
        # -----------------------------------------------------

        vendor = first_match([
            r"\b(?:vendor|seller|supplier|merchant|issued\s*by|"
            r"provided\s*by|sold\s*by)\s*[:\-]?\s*([^\n]+)"
        ], text)

        if vendor:
            vendor = clean_business_name(vendor)

        # If there is no explicit vendor label,
        # look at the beginning of the document.
        if vendor is None:

            ignored = re.compile(
                r"invoice|receipt|tax\s*invoice|date|"
                r"invoice\s*(?:number|no|#|h)|"
                r"bill\s*to|ship\s*to|customer|"
                r"address|street|road|avenue|lane|"
                r"boulevard|drive|phone|telephone|tel|"
                r"fax|email|website|gst|vat|tax|"
                r"total|subtotal|amount",
                re.IGNORECASE
            )

            for line in document_lines[:10]:

                candidate = line.strip(" []")

                if len(candidate) < 2:
                    continue

                if ignored.search(candidate):
                    continue

                if not re.search(r"[A-Za-z]", candidate):
                    continue

                # Reject mostly-numeric lines.
                if len(re.findall(r"\d", candidate)) > len(
                    re.findall(r"[A-Za-z]", candidate)
                ):
                    continue

                vendor = clean_business_name(candidate)

                if vendor:
                    break

        # -----------------------------------------------------
        # INVOICE DATE
        # -----------------------------------------------------

        invoice_date = first_match([
            r"\b(?:invoice\s*)?date\s*[:\-]?\s*"
            r"([0-9]{1,2}[\/\-.][0-9]{1,2}[\/\-.][0-9]{2,4})",

            r"\b(?:invoice\s*)?date\s*[:\-]?\s*"
            r"([0-9]{1,2}\s+[A-Za-z]{3,12}\s+[0-9]{4})",

            r"\b(?:invoice\s*)?date\s*[:\-]?\s*"
            r"([A-Za-z]{3,12}\s+[0-9]{1,2},?\s+[0-9]{4})",
        ], text)

        # -----------------------------------------------------
        # DUE DATE
        # -----------------------------------------------------

        due_date = first_match([
            r"\bdue\s*date\s*[:\-]?\s*"
            r"([0-9]{1,2}[\/\-.][0-9]{1,2}[\/\-.][0-9]{2,4})",

            r"\bdue\s*date\s*[:\-]?\s*"
            r"([0-9]{1,2}\s+[A-Za-z]{3,12}\s+[0-9]{4})",

            r"\bdue\s*date\s*[:\-]?\s*"
            r"([A-Za-z]{3,12}\s+[0-9]{1,2},?\s+[0-9]{4})",
        ], text)

        # -----------------------------------------------------
        # SUBTOTAL
        # -----------------------------------------------------

        subtotal = first_match([
            rf"\bsub\s*total\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\bsubtotal\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\bsub\s*total\b[^\d₹$€£]*"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        # -----------------------------------------------------
        # TAX
        # -----------------------------------------------------

        tax = first_match([

            # Tax (5%) 12.00
            rf"\b(?:sales\s*)?(?:tax|gst|vat)\b"
            rf"\s*\(\s*\d+(?:\.\d+)?\s*%[^)]*\)"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            # Tax (4.25% after discount) 28.56
            rf"\b(?:sales\s*)?(?:tax|gst|vat)\b"
            rf"\s*\([^)]*%\s*[^)]*\)"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            # Tax 5% 12.00
            rf"\b(?:sales\s*)?(?:tax|gst|vat)\b"
            rf"\s+\d+(?:\.\d+)?\s*%\s*"
            rf"[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            # Tax Amount: 439.20
            rf"\b(?:tax\s*amount|tax\s*due|taxable\s*tax)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            # Tax: 439.20
            rf"\b(?:tax|gst|vat)\b"
            rf"(?!\s*(?:rate|percentage|registered|registration|"
            rf"id|number|no\.?))"
            rf"\s*[:\-]\s*{CURRENCY}\s*({NUMBER})",

            # Tax
            # 439.20
            rf"\b(?:tax|gst|vat)\b"
            rf"(?!\s*(?:rate|percentage|registered|registration|"
            rf"id|number|no\.?))"
            rf"\s*\n\s*{CURRENCY}\s*({NUMBER})",

            # Tax 439.20
            rf"\b(?:tax|gst|vat)\b"
            rf"(?!\s*(?:rate|percentage|registered|registration|"
            rf"id|number|no\.?))"
            rf"\s+{CURRENCY}\s*({NUMBER})",

            # OCR may insert text between label and value.
            rf"\b(?:tax|gst|vat)\b"
            rf"(?!\s*(?:rate|percentage|registered|registration|"
            rf"id|number|no\.?))"
            rf"[^0-9₹$€£%]{{0,40}}"
            rf"{CURRENCY}\s*({NUMBER})",

        ], text)

        # -----------------------------------------------------
        # TOTAL
        # -----------------------------------------------------

        total = first_match([

            # Total Due $3,367.20
            rf"\btotal\s*due\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            # Grand Total
            rf"\bgrand\s*total\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            # Total Amount
            rf"\btotal\s*amount\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            # Total (USD) $252.00
            rf"\btotal\b\s*\([^)]*\)"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            # Total: $252.00
            rf"(?m)^\s*total\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            # Total $252.00
            rf"\btotal\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            # Total
            # $252.00
            rf"\btotal\b\s*[:\-]?\s*\n\s*"
            rf"{CURRENCY}\s*({NUMBER})",
        ], text)

        return {
            "invoice_number": invoice_number,
            "vendor": vendor,
            "invoice_date": invoice_date,
            "due_date": due_date,
            "subtotal": subtotal,
            "tax": tax,
            "total": total
        }

    # =========================================================
    # PAYSLIP
    # =========================================================

    elif document_type == "payslip":

        

        employee_name = first_match([
            r"\bemployee\s*name\s*[:\-]?\s*([^\n]+)",

            r"\bemployee\s*name\s*\n\s*([^\n]+)",

            r"\bemployee\s*[:\-]?\s*([^\n]+)",

            r"\bname\s*[:\-]?\s*([^\n]+)",
        ], text)


        

        employee_id = first_match([
            r"\bemployee\s*(?:id|number|no\.?|#)"
            r"\s*[:\-]?\s*"
            r"([A-Za-z0-9][A-Za-z0-9\-_\/]*)",

            r"\bemp\s*(?:id|number|no\.?|#)"
            r"\s*[:\-]?\s*"
            r"([A-Za-z0-9][A-Za-z0-9\-_\/]*)",
        ], text)


        # -----------------------------------------------------
        # EMPLOYER
        # -----------------------------------------------------

        employer = None

        employer_patterns = [
            r"\bemployer\s*(?:name)?\s*[:\-]\s*([^\n]+)",
            r"\bemployer\s*(?:name)?\s*\n\s*([^\n]+)",

            r"\bcompany\s*(?:name)?\s*[:\-]\s*([^\n]+)",
            r"\bcompany\s*(?:name)?\s*\n\s*([^\n]+)",
        ]

        for pattern in employer_patterns:

            match = re.search(pattern, text, re.IGNORECASE)

            if not match:
                continue

            candidate = match.group(1).strip(" []")

            # NEVER accept signature as employer
            if re.search(r"\bsignature\b", candidate, re.IGNORECASE):
                continue

            if candidate:
                employer = candidate
                break


        # -----------------------------------------------------
        # FALLBACK: COMPANY NAME NEAR TOP OF PAYSLIP
        # -----------------------------------------------------

        if employer is None:

            lines = [
                line.strip(" []")
                for line in text.splitlines()
                if line.strip()
            ]

            ignored = re.compile(
                r"\b(?:payslip|pay\s*slip|"
                r"date|date\s+of\s+joining|"
                r"employee(?:\s+name)?|"
                r"designation|department|"
                r"pay\s+period|worked\s+days|"
                r"earnings|deductions|amount|"
                r"signature|"
                r"employer\s+signature|"
                r"employee\s+signature|"
                r"gross|net\s*pay|net\s*salary|"
                r"total\s+earnings|total\s+deductions)\b",
                re.IGNORECASE
            )

            address_pattern = re.compile(
                r"\b(?:street|st\.?|road|rd\.?|avenue|ave\.?|"
                r"lane|ln\.?|boulevard|blvd\.?|drive|dr\.?|"
                r"highway|hwy\.?)\b",
                re.IGNORECASE
            )

            for line in lines[:10]:

                candidate = line.strip()

                if not candidate:
                    continue

                if ignored.search(candidate):
                    continue

                if address_pattern.search(candidate):
                    continue

                if re.search(
                    r"\b(?:phone|telephone|tel|email|fax)\b",
                    candidate,
                    re.IGNORECASE
                ):
                    continue

                if not re.search(r"[A-Za-z]", candidate):
                    continue

                employer = candidate
                break

        # -----------------------------------------------------
        # PAY PERIOD
        # -----------------------------------------------------

        pay_period = first_match([
            r"\bpay\s*period\s*[:\-]?\s*([^\n]+)",

            r"\bpay\s*period\s*\n\s*([^\n]+)",

            r"\bpay\s*cycle\s*[:\-]?\s*([^\n]+)",

            r"\bperiod\s*[:\-]?\s*([^\n]+)",
        ], text)


        # -----------------------------------------------------
        # BASIC SALARY
        # -----------------------------------------------------

        basic_salary = first_match([
            rf"\bbasic\s*(?:salary|pay|wages)?\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\bbasic\s*(?:salary|pay|wages)?\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ], text)


        # -----------------------------------------------------
        # HRA
        # -----------------------------------------------------

        hra = first_match([
            rf"\b(?:hra|house\s*rent\s*allowance)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\b(?:hra|house\s*rent\s*allowance)\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ], text)


        # -----------------------------------------------------
        # GROSS SALARY
        #
        # Supports:
        # Gross Salary
        # Gross Pay
        # Gross Earnings
        # Total Earnings
        # Total Gross
        # -----------------------------------------------------

        gross_salary = first_match([
            rf"\bgross\s*(?:salary|pay|earnings|income)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\bgross\s*(?:salary|pay|earnings|income)\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\btotal\s*earnings?\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\btotal\s*earnings?\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\btotal\s*gross\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",
        ], text)


        # -----------------------------------------------------
        # TOTAL DEDUCTIONS
        # -----------------------------------------------------

        total_deductions = first_match([
            rf"\btotal\s*deductions?\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\btotal\s*deductions?\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ], text)


        # -----------------------------------------------------
        # TAX DEDUCTED
        # -----------------------------------------------------

        tax_deducted = first_match([
            # Tax Deducted: 500
            rf"\b(?:tax\s*deducted|income\s*tax|tds)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            # Tax Deducted 500
            rf"\b(?:tax\s*deducted|income\s*tax|tds)\b"
            rf"\s*[:\-]?\s*{CURRENCY}?\s*({NUMBER})",

            # Professional Tax: 500
            rf"\bprofessional\s*tax\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            # Professional Tax 500
            rf"\bprofessional\s*tax\b"
            rf"\s*[:\-]?\s*{CURRENCY}?\s*({NUMBER})",

        ], text)


        # -----------------------------------------------------
        # PROVIDENT FUND
        # -----------------------------------------------------

        provident_fund = first_match([
            rf"\b(?:provident\s*fund|pf|epf)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\b(?:provident\s*fund|pf|epf)\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ], text)


        # -----------------------------------------------------
        # NET SALARY
        # -----------------------------------------------------

        net_salary = first_match([
            rf"\b(?:net\s*salary|net\s*pay|take\s*home\s*pay|"
            rf"net\s*earnings)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\b(?:net\s*salary|net\s*pay|take\s*home\s*pay|"
            rf"net\s*earnings)\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ], text)


        return {
            "employee_name": employee_name,
            "employee_id": employee_id,
            "employer": employer,
            "pay_period": pay_period,
            "basic_salary": basic_salary,
            "hra": hra,
            "gross_salary": gross_salary,
            "total_deductions": total_deductions,
            "tax_deducted": tax_deducted,
            "provident_fund": provident_fund,
            "net_salary": net_salary
        }

    # =========================================================
    # BANK STATEMENT
    # =========================================================

    elif document_type == "bank_statement":

        account_holder = first_match([
            r"\baccount\s*holder\s*[:\-]?\s*([^\n]+)",
            r"\baccount\s*name\s*[:\-]?\s*([^\n]+)",
        ], text)

        account_number = first_match([
            r"\baccount\s*(?:number|no\.?|#)"
            r"\s*[:\-]?\s*"
            r"([0-9Xx*][0-9Xx*\- ]{3,})",

            r"\ba\/c\s*(?:number|no\.?|#)"
            r"\s*[:\-]?\s*"
            r"([0-9Xx*\- ]{3,})",
        ])

        if account_number:
            account_number = account_number.strip()

        bank_name = first_match([
            r"\bbank\s*name\s*[:\-]?\s*([^\n]+)",
            r"\bbank\s*[:\-]?\s*([^\n]+)",
        ], text)

        statement_period = first_match([
            r"\bstatement\s*period\s*[:\-]?\s*([^\n]+)",
            r"\bstatement\s*date\s*[:\-]?\s*([^\n]+)",
            r"\bperiod\s*[:\-]?\s*([^\n]+)",
        ], text)

        opening_balance = first_match([
            rf"\b(?:opening|beginning|starting|start)"
            rf"\s*balance\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\b(?:opening|beginning|starting|start)"
            rf"\s*balance\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        closing_balance = first_match([
            rf"\b(?:closing|ending|end)"
            rf"\s*balance\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\b(?:closing|ending|end)"
            rf"\s*balance\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        transactions = []

        for line in document_lines:

            date_match = re.search(
                r"\b\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}\b",
                line
            )

            if not date_match:
                continue

            amounts = re.findall(
                rf"{CURRENCY}\s*({NUMBER})",
                line
            )

            if not amounts:
                continue

            amount = amounts[-1]

            description = line[
                date_match.end():
            ].strip()

            description = re.sub(
                rf"{CURRENCY}\s*{NUMBER}\s*$",
                "",
                description
            ).strip(" -:")

            transactions.append({
                "date": date_match.group(0),
                "amount": amount,
                "description": description
            })

        return {
            "account_holder": account_holder,
            "account_number": account_number,
            "bank_name": bank_name,
            "statement_period": statement_period,
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "transactions": transactions
        }

    # =========================================================
    # RECEIPT
    # =========================================================

    elif document_type == "receipt":

        # -----------------------------------------------------
        # MERCHANT
        # -----------------------------------------------------

        merchant = first_match([
            r"\bmerchant\s*[:\-]?\s*([^\n]+)",
            r"\bseller\s*[:\-]?\s*([^\n]+)",
            r"\bstore\s*[:\-]?\s*([^\n]+)",
            r"\bshop\s*[:\-]?\s*([^\n]+)",
        ], text)

        if merchant:
            merchant = clean_business_name(merchant)

        if merchant is None:

            ignored = re.compile(
                r"receipt|invoice|date|"
                r"receipt\s*(?:number|no|#)|"
                r"bill\s*to|billed\s*to|customer|"
                r"address|street|phone|telephone|tel|"
                r"email|subtotal|tax|gst|vat|"
                r"total|amount|payment",
                re.IGNORECASE
            )

            for line in document_lines[:8]:

                candidate = line.strip(" []")

                if len(candidate) < 2:
                    continue

                if ignored.search(candidate):
                    continue

                if not re.search(r"[A-Za-z]", candidate):
                    continue

                merchant = clean_business_name(candidate)

                if merchant:
                    break

        # -----------------------------------------------------
        # RECEIPT NUMBER
        # -----------------------------------------------------

        receipt_number = first_match([
            r"\breceipt\s*(?:number|num(?:ber)?|no\.?|#|id)"
            r"\s*[:\-]?\s*"
            r"([A-Za-z0-9][A-Za-z0-9\-_\/]*)",
        ])

        # -----------------------------------------------------
        # TRANSACTION DATE
        # -----------------------------------------------------

        transaction_date = first_match([
            r"\btransaction\s*date\s*[:\-]?\s*"
            r"([0-9]{1,2}[\/\-.][0-9]{1,2}[\/\-.][0-9]{2,4})",

            r"\breceipt\s*date\s*[:\-]?\s*"
            r"([0-9]{1,2}[\/\-.][0-9]{1,2}[\/\-.][0-9]{2,4})",

            r"\bdate\s*[:\-]?\s*"
            r"([0-9]{1,2}[\/\-.][0-9]{1,2}[\/\-.][0-9]{2,4})",

            r"\b(?:transaction\s*)?date\s*[:\-]?\s*"
            r"([0-9]{1,2}\s+[A-Za-z]{3,12}\s+[0-9]{4})",

            r"\b(?:transaction\s*)?date\s*[:\-]?\s*"
            r"([A-Za-z]{3,12}\s+[0-9]{1,2},?\s+[0-9]{4})",
        ], text)

        # -----------------------------------------------------
        # RECEIPT ITEMS
        # -----------------------------------------------------

        items = []

        for line in document_lines:

            # Never treat summary rows as items.
            if re.search(
                r"\b(?:subtotal|sub\s*total|tax|gst|vat|"
                r"total|amount\s*due|sales\s*tax)\b",
                line,
                re.IGNORECASE
            ):
                continue

            # -------------------------------------------------
            # Quantity + Description + Unit Price + Amount
            #
            # 2 Product A 45.00 $90.00
            # -------------------------------------------------

            item_match = re.match(
                rf"^\s*(\d+)\s+(.+?)\s+"
                rf"{CURRENCY}\s*({NUMBER})\s+"
                rf"{CURRENCY}\s*({NUMBER})\s*$",
                line,
                re.IGNORECASE
            )

            if item_match:

                items.append({
                    "quantity": item_match.group(1),
                    "description": item_match.group(2).strip(),
                    "unit_price": item_match.group(3),
                    "amount": item_match.group(4)
                })

                continue

            # -------------------------------------------------
            # Quantity + Description + Amount
            #
            # 2 Product A 90.00
            # -------------------------------------------------

            item_match = re.match(
                rf"^\s*(\d+)\s+(.+?)\s+"
                rf"{CURRENCY}\s*({NUMBER})\s*$",
                line,
                re.IGNORECASE
            )

            if item_match:

                items.append({
                    "quantity": item_match.group(1),
                    "description": item_match.group(2).strip(),
                    "unit_price": None,
                    "amount": item_match.group(3)
                })

                continue

            # -------------------------------------------------
            # Description + currency + amount
            #
            # Product A $90.00
            #
            # Currency is REQUIRED here.
            # This prevents addresses such as:
            # "Company Town, ST 12345"
            # from becoming items.
            # -------------------------------------------------

            item_match = re.match(
                rf"^\s*(?!\d+\s+)"
                rf"(.+?)\s+"
                rf"([₹$€£]|Rs\.?|INR)\s*"
                rf"({NUMBER})\s*$",
                line,
                re.IGNORECASE
            )

            if item_match:

                items.append({
                    "quantity": None,
                    "description": item_match.group(1).strip(),
                    "unit_price": None,
                    "amount": item_match.group(3)
                })

        # -----------------------------------------------------
        # SUBTOTAL
        # -----------------------------------------------------

        subtotal = first_match([
            rf"\bsub\s*total\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\bsubtotal\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\bsub\s*total\b[^\d₹$€£]*"
            rf"{CURRENCY}\s*({NUMBER})",
        ], text)

        # -----------------------------------------------------
        # TAX
        # -----------------------------------------------------

        tax = first_match([

            rf"\b(?:sales\s*)?(?:tax|gst|vat)\b"
            rf"\s*\([^)]*%\s*[^)]*\)"
            rf"\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\b(?:sales\s*)?(?:tax|gst|vat)\b"
            rf"\s+\d+(?:\.\d+)?\s*%\s*"
            rf"[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\b(?:tax\s*amount|tax\s*due)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\b(?:tax|gst|vat)\b"
            rf"(?!\s*(?:rate|percentage|registered|registration|"
            rf"id|number|no\.?))"
            rf"\s*[:\-]\s*{CURRENCY}\s*({NUMBER})",

            rf"\b(?:tax|gst|vat)\b"
            rf"(?!\s*(?:rate|percentage|registered|registration|"
            rf"id|number|no\.?))"
            rf"\s*\n\s*{CURRENCY}\s*({NUMBER})",

            rf"\b(?:tax|gst|vat)\b"
            rf"(?!\s*(?:rate|percentage|registered|registration|"
            rf"id|number|no\.?))"
            rf"\s+{CURRENCY}\s*({NUMBER})",

            rf"\b(?:tax|gst|vat)\b"
            rf"(?!\s*(?:rate|percentage|registered|registration|"
            rf"id|number|no\.?))"
            rf"[^0-9₹$€£%]{{0,40}}"
            rf"{CURRENCY}\s*({NUMBER})",

        ], text)

        # -----------------------------------------------------
        # TOTAL AMOUNT
        # -----------------------------------------------------

        total_amount = first_match([

            rf"\btotal\b\s*\([^)]*\)"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\btotal\s*amount\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\bamount\s*due\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\bgrand\s*total\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\btotal\s*due\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"(?m)^\s*total\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\btotal\b\s*[:\-]?\s*"
            rf"{CURRENCY}\s*({NUMBER})",

            rf"\btotal\b\s*[:\-]?\s*\n\s*"
            rf"{CURRENCY}\s*({NUMBER})",
        ], text)

        # -----------------------------------------------------
        # PAYMENT METHOD
        # -----------------------------------------------------

        payment_method = first_match([
            r"\bpayment\s*method\s*[:\-]?\s*([^\n]+)",
            r"\bpayment\s*type\s*[:\-]?\s*([^\n]+)",
            r"\bpaid\s*by\s*[:\-]?\s*([^\n]+)",
            r"\bpayment\s*mode\s*[:\-]?\s*([^\n]+)",
        ], text)

        return {
            "merchant": merchant,
            "receipt_number": receipt_number,
            "transaction_date": transaction_date,
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "total_amount": total_amount,
            "payment_method": payment_method
        }

    # =========================================================
    # TAX DOCUMENT
    # =========================================================

    elif document_type == "tax_document":

        taxpayer_name = first_match([
            r"\btaxpayer\s*name\s*[:\-]?\s*([^\n]+)",
            r"\btaxpayer\s*[:\-]?\s*([^\n]+)",
            r"\bname\s*[:\-]?\s*([^\n]+)",
        ], text)

        taxpayer_id = first_match([
            r"\btaxpayer\s*(?:id|number|no\.?|#)"
            r"\s*[:\-]?\s*"
            r"([A-Za-z0-9\-_\/]+)",

            r"\btax\s*id\s*[:\-]?\s*"
            r"([A-Za-z0-9\-_\/]+)",

            r"\b(?:tin|pan)\s*[:\-]?\s*"
            r"([A-Za-z0-9\-_\/]+)",
        ])

        tax_year = first_match([
            r"\btax\s*year\s*[:\-]?\s*"
            r"((?:19|20)\d{2}\s*[-\/]\s*(?:19|20)?\d{2,4})",

            r"\btax\s*year\s*[:\-]?\s*"
            r"((?:19|20)\d{2})",
        ])

        assessment_year = first_match([
            r"\bassessment\s*year\s*[:\-]?\s*"
            r"((?:19|20)\d{2}\s*[-\/]\s*(?:19|20)?\d{2,4})",

            r"\bassessment\s*year\s*[:\-]?\s*"
            r"((?:19|20)\d{2})",
        ])

        gross_income = first_match([
            rf"\bgross\s*(?:income|total\s*income)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\bgross\s*(?:income|total\s*income)\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        taxable_income = first_match([
            rf"\btaxable\s*income\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\btaxable\s*income\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        deductions = first_match([
            rf"\btotal\s*deductions?\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\bdeductions?\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\bdeductions?\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        tax_paid = first_match([
            rf"\btax\s*paid\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\btax\s*withheld\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\bwithholding\s*tax\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\btax\s*paid\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        tax_liability = first_match([
            rf"\btax\s*(?:liability|due|owed)\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\btax\s*(?:liability|due|owed)\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        refund_amount = first_match([
            rf"\brefund\s*(?:amount|due)?\b"
            rf"\s*[:\-]?\s*{CURRENCY}\s*({NUMBER})",

            rf"\brefund\s*(?:amount|due)?\b"
            rf"[^0-9₹$€£]{{0,30}}"
            rf"{CURRENCY}\s*({NUMBER})",
        ])

        return {
            "taxpayer_name": taxpayer_name,
            "taxpayer_id": taxpayer_id,
            "tax_year": tax_year,
            "assessment_year": assessment_year,
            "gross_income": gross_income,
            "taxable_income": taxable_income,
            "deductions": deductions,
            "tax_paid": tax_paid,
            "tax_liability": tax_liability,
            "refund_amount": refund_amount
        }

    return _extract_extended_metadata(text, document_type)