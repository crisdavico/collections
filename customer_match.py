# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""Match one seller query to a connector customer.

Callers still require exactly one seller-scoped row. This predicate is true
for every row the query could mean, including an ambiguous numeric tail.
"""

from __future__ import annotations


def trim_code(value: object) -> str:
    """Strip whitespace and leading-zero pad; keep a lone ``0``."""
    if value in (None, False):
        return ""
    text = str(value).strip()
    if not text:
        return text
    stripped = text.lstrip("0")
    return stripped if stripped else "0"


def canonicalize_cuit(value: object) -> str:
    """Format 11-digit values as AFIP ``XX-XXXXXXXX-X``; otherwise strip."""
    if value in (None, False):
        return ""
    text = str(value).strip()
    digits = "".join(char for char in text if char.isdigit())
    if len(digits) == 11:
        return f"{digits[:2]}-{digits[2:10]}-{digits[10]}"
    return text


def _trailing_digits(customer_code: object) -> str:
    """Digits the customer code ends with, or ``""`` when it does not."""
    if customer_code in (None, False):
        return ""
    text = str(customer_code).strip()
    end = len(text)
    while end > 0 and text[end - 1].isdigit():
        end -= 1
    return text[end:]


def matches_customer_query(
    identification: object, customer_code: object, query: object
) -> bool:
    """Return whether ``query`` selects this customer.

    A CUIT matches in canonical ``XX-XXXXXXXX-X`` form, with or without
    hyphens. A customer code matches with leading zeros stripped and case
    ignored, so ``000123`` and ``ns0160`` select ``123`` and ``NS0160``.
    A shorter all-digit query matches the trailing digits of the code, so
    ``0160`` selects ``NS0160``. An 11-digit query is only a CUIT: it must
    not also match some other code that happens to end with those digits.
    """
    if query in (None, False):
        return False
    text = str(query).strip()
    if not text:
        return False
    stored_identification = canonicalize_cuit(identification)
    if stored_identification and stored_identification == canonicalize_cuit(text):
        return True
    stored_code = trim_code(customer_code)
    asked_code = trim_code(text)
    if stored_code and asked_code and stored_code.casefold() == asked_code.casefold():
        return True
    if text.isdigit() and len(text) != 11:
        suffix = _trailing_digits(customer_code)
        if suffix and trim_code(suffix) == trim_code(text):
            return True
    return False
