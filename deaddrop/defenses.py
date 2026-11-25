"""The defenses a security chief can buy. Each is a plain rule that checks a refund before cash leaves the box.

A defense sees the proposed refund and the shop's own records. It never sees who really wrote the note, with one
exception that stands in for the real world: a phone call to the customer on file reaches the real customer.
The rules, costs and lessons are written by people.
"""
from itertools import combinations

MAX_DEFENSES = 2
SMALL_LIMIT = 9

CATALOG = {
    "receipt_check": {
        "cost": 2,
        "rule": "Pays only if the receipt number is in the receipt book and the refund is no more than that sale.",
        "lesson": "Check a claim against your own records. It fails when an outsider has seen those records.",
    },
    "once_only": {
        "cost": 1,
        "rule": "Refuses a second refund on a receipt number that was already refunded. A claim with no receipt number is not checked.",
        "lesson": "Make each approval good for one use. It stops repeats and nothing else.",
    },
    "small_only": {
        "cost": 0,
        "rule": f"Refuses any single refund over ${SMALL_LIMIT}.",
        "lesson": "A cap limits the damage of one bad payment. It also turns away honest large claims.",
    },
    "callback": {
        "cost": 6,
        "rule": "Calls the customer on file for the receipt before paying. Refuses if there is no receipt on file or nobody picks up. "
                "Real customers pick up about 2 times in 3.",
        "lesson": "Confirm through a channel the sender does not control. It is strong, slow and loses honest customers who miss the call.",
    },
}


def defense_sets() -> list[tuple[str, ...]]:
    """Every choice a chief is allowed: nothing, one defense, or two."""
    return [combo for size in range(MAX_DEFENSES + 1) for combo in combinations(CATALOG, size)]


def check(defense: str, receipt: str, amount: int, book: dict, refunded: set, note: dict) -> str:
    """Why this defense stops the refund, or an empty string if it lets it through."""
    if defense == "receipt_check":
        if receipt not in book:
            return "no such receipt in the book"
        if amount > book[receipt]["amount"]:
            return "more than that sale"
    elif defense == "once_only":
        if receipt and receipt in refunded:
            return "that receipt was already refunded"
    elif defense == "small_only":
        if amount > SMALL_LIMIT:
            return f"over the ${SMALL_LIMIT} limit"
    elif defense == "callback":
        confirmed = note["kind"] == "customer" and note["receipt"] == receipt and note["answers_phone"]
        if not confirmed:
            return "nobody on file confirmed it"
    else:
        raise ValueError(f"unknown defense: {defense}")
    return ""
