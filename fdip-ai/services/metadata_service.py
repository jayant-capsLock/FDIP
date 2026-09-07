import re


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

    return None