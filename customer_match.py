# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""Match one seller query to a connector customer.

Callers still require exactly one seller-scoped row. This predicate is true
for every row the query could mean, including an ambiguous numeric tail.
``search_customers`` ranks the rows a looser query (part of a name, code or
CUIT) may mean, so the agent can ask the seller to pick one.
"""

from __future__ import annotations

import difflib
import re
import unicodedata


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


CUSTOMER_SEARCH_LIMIT = 10
_SIMILAR_RATIO = 0.8


def _fold(value: object) -> str:
    """Lowercase words without accents; dots join (``S.R.L.`` is ``srl``)."""
    if value in (None, False):
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace(".", "")
    return " ".join(re.sub(r"[^0-9a-z]+", " ", text).split())


def _is_partial_match(customer: dict, words: list[str]) -> bool:
    """Every word is inside the name, or the query is inside the code or CUIT."""
    name = _fold(customer.get("name"))
    if all(word in name for word in words):
        return True
    compact = "".join(words)
    if compact in _fold(customer.get("customer_code")).replace(" ", ""):
        return True
    identification = _fold(customer.get("identification")).replace(" ", "")
    return compact.isdigit() and compact in identification


def _similarity(customer: dict, words: list[str]) -> float:
    """How close the furthest query word is to its nearest name word."""
    names = _fold(customer.get("name")).split()
    if not names:
        return 0.0
    return min(
        max(difflib.SequenceMatcher(None, word, name).ratio() for name in names)
        for word in words
    )


def search_customers(
    customers: list[dict], query: object, limit: int = CUSTOMER_SEARCH_LIMIT
) -> dict:
    """Return the customers ``query`` may mean, best first.

    ``exact`` is a CUIT, code, or numeric code tail (``matches_customer_query``).
    ``partial`` has every query word inside the name, or the query inside the
    code or the CUIT digits; case, accents and punctuation are ignored.
    ``similar`` is only tried when nothing else matched: every query word is
    close to a name word, so a typo still finds the customer. Each row gains
    ``match``; at most ``limit`` rows come back, with ``total_matches`` and
    ``truncated``.
    """
    words = _fold(query).split()
    ranked = []
    for customer in customers:
        if matches_customer_query(
            customer.get("identification"), customer.get("customer_code"), query
        ):
            ranked.append((0, 0.0, customer, "exact"))
        elif words and _is_partial_match(customer, words):
            ranked.append((1, 0.0, customer, "partial"))
    if not ranked and words:
        for customer in customers:
            score = _similarity(customer, words)
            if score >= _SIMILAR_RATIO:
                ranked.append((2, -score, customer, "similar"))
    ranked.sort(key=lambda item: (item[0], item[1], _fold(item[2].get("name"))))
    matches = [{**customer, "match": kind} for _tier, _score, customer, kind in ranked]
    return {
        "customers": matches[:limit],
        "total_matches": len(matches),
        "truncated": len(matches) > limit,
    }
