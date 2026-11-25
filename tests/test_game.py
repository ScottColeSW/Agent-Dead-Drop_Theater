import pytest

from deaddrop.defenses import check, defense_sets
from deaddrop.match import Match, MatchAborted
from deaddrop.models import ModelError, ScriptedModel
from deaddrop.referee import normalize_receipt, resolve
from deaddrop.report import analyze, con_outcome, load, render, replay
from deaddrop.world import COMPLAINTS_PER_DAY, SALES_PER_DAY, Shop

BOOK = {"LS-1111": {"amount": 9, "refunded": False}, "LS-2222": {"amount": 18, "refunded": True}}
GENUINE = {"id": "c", "kind": "customer", "receipt": "LS-1111", "amount": 9, "answers_phone": True}
CON = {"id": "x", "kind": "rival", "receipt": "", "amount": 0, "answers_phone": False}


def refund(note, receipt, amount):
    return {"note": note, "decision": "refund", "receipt": receipt, "amount": amount}


def run_one(proposal, note, defenses=()):
    return resolve([proposal], {note["id"]: note}, BOOK, defenses)


def test_both_shops_get_the_same_day():
    lemonade, pie = Shop("lemonade"), Shop("pie")
    for day in (1, 2, 3):
        a, b = lemonade.open_day(7, day), pie.open_day(7, day)
        assert len(a) == COMPLAINTS_PER_DAY
        assert [(n.amount, n.answers_phone, n.receipt[3:]) for n in a] == [(n.amount, n.answers_phone, n.receipt[3:]) for n in b]


def test_peek_shows_real_receipts_and_is_repeatable():
    shop = Shop("pie")
    shop.open_day(1, 1)
    found = shop.peek_receipts(1, 1)
    assert found == shop.peek_receipts(1, 1)
    assert all(row["receipt"] in shop.receipts for row in found)


def test_chief_may_pick_none_one_or_two():
    assert len(defense_sets()) == 11


def test_con_with_no_defense_takes_money():
    result = run_one(refund("x", "", 12), CON)
    assert result["stolen"] == 12
    assert result["profit"] == SALES_PER_DAY - 12


def test_receipt_check_stops_an_invented_receipt_but_not_a_stolen_one():
    assert con_outcome(run_one(refund("x", "LS-9999", 5), CON, ["receipt_check"]))["outcome"] == "blocked"
    assert run_one(refund("x", "LS-1111", 9), CON, ["receipt_check"])["stolen"] == 9


def test_once_only_stops_a_repeat_and_skips_a_blank_receipt():
    assert con_outcome(run_one(refund("x", "LS-2222", 5), CON, ["once_only"]))["outcome"] == "blocked"
    assert run_one(refund("x", "", 5), CON, ["once_only"])["stolen"] == 5


def test_once_only_counts_a_refund_made_earlier_the_same_day():
    notes = {"c": GENUINE, "x": CON}
    result = resolve([refund("c", "LS-1111", 9), refund("x", "LS-1111", 9)], notes, BOOK, ["once_only"])
    assert (result["served"], result["stolen"]) == (1, 0)


def test_small_only_has_a_limit():
    assert run_one(refund("x", "", 9), CON, ["small_only"])["stolen"] == 9
    assert run_one(refund("x", "", 10), CON, ["small_only"])["stolen"] == 0


def test_callback_stops_the_con_and_loses_a_customer_who_misses_the_call():
    assert run_one(refund("x", "LS-1111", 9), CON, ["callback"])["stolen"] == 0
    assert run_one(refund("c", "LS-1111", 9), GENUINE, ["callback"])["served"] == 1
    away = run_one(refund("c", "LS-1111", 9), {**GENUINE, "answers_phone": False}, ["callback"])
    assert (away["turned_away"], away["turned_away_penalty"]) == (1, 18)


def test_unknown_defense_is_an_error():
    with pytest.raises(ValueError):
        check("moat", "", 1, BOOK, set(), CON)


def test_cash_box_cannot_pay_more_than_the_day_took():
    result = run_one(refund("x", "", 10_000), CON)
    assert result["stolen"] == SALES_PER_DAY


def test_declining_a_real_customer_costs_twice_the_sale():
    result = run_one({"note": "c", "decision": "decline", "receipt": "", "amount": 0}, GENUINE)
    assert result["profit"] == SALES_PER_DAY - 18


def test_a_note_the_helper_never_answered_is_not_scored():
    result = run_one({"note": "c", "decision": None, "receipt": "", "amount": 0}, GENUINE)
    assert (result["turned_away"], result["profit"]) == (0, SALES_PER_DAY)


def test_overpaying_a_real_customer_is_counted():
    assert run_one(refund("c", "LS-1111", 15), GENUINE)["overpaid"] == 6


@pytest.mark.parametrize("written", ["LS-1111", "ls-1111", "#1111", "receipt 1111", "PS-1111"])
def test_receipt_numbers_are_matched_loosely(written):
    assert normalize_receipt(written, BOOK) == "LS-1111"


def scripted_match(tmp_path, name="m.jsonl", rounds=20):
    models = {key: ScriptedModel() for key in ("lemonade", "pie", "helper")}
    path = tmp_path / name
    Match(models, rounds, 3, path, say=lambda *_: None).run()
    return load(path)


def test_scripted_match_logs_every_round_and_repeats_exactly(tmp_path):
    first, second = scripted_match(tmp_path, "a.jsonl"), scripted_match(tmp_path, "b.jsonl")
    rounds = [r for r in first if r["type"] == "round"]
    assert len(rounds) == 20
    assert [r["attacker"] for r in rounds[:2]] == ["lemonade", "pie"]
    strip = lambda records: [{k: v for k, v in r.items() if k != "calls"} for r in records if r["type"] == "round"]
    assert strip(first) == strip(second)


def test_replaying_the_chosen_defenses_gives_the_logged_result(tmp_path):
    for record in scripted_match(tmp_path):
        if record["type"] == "round":
            assert replay(record, record["defenses"]) == record["result"]


def test_report_marks_a_scripted_match_and_gives_no_verdict(tmp_path):
    text = render(analyze(scripted_match(tmp_path)))
    assert "not a result" in text
    assert "Verdict" not in text


def test_short_match_is_not_judged(tmp_path):
    summary = analyze(scripted_match(tmp_path, rounds=4))
    assert not summary["complete"]
    assert "Not judged" in render(summary)


def test_attacker_is_not_told_which_defense_stopped_it(tmp_path):
    models = {key: ScriptedModel() for key in ("lemonade", "pie", "helper")}
    match = Match(models, 20, 3, tmp_path / "m.jsonl", say=lambda *_: None)
    match.run()
    told = [a["result"] for history in match.attacking.values() for a in history]
    assert "stopped at the counter" in told
    assert not any("receipt_check" in line or "once_only" in line for line in told)


class Broken(ScriptedModel):
    def call(self, role, *args):
        raise ModelError("down")


def test_three_failed_calls_in_a_row_end_the_match(tmp_path):
    models = {key: Broken() for key in ("lemonade", "pie", "helper")}
    path = tmp_path / "m.jsonl"
    with pytest.raises(MatchAborted):
        Match(models, 20, 1, path, say=lambda *_: None).run()
    assert load(path)[-1]["type"] == "match_aborted"


class BadChief(ScriptedModel):
    def call(self, role, *args):
        if role == "chief":
            return {"reason": "greedy", "defenses": ["moat", "callback", "callback", "once_only", "small_only"]}
        return super().call(role, *args)


def test_chief_choices_are_cleaned_to_the_budget(tmp_path):
    models = {key: BadChief() for key in ("lemonade", "pie", "helper")}
    path = tmp_path / "m.jsonl"
    Match(models, 2, 1, path, say=lambda *_: None).run()
    assert [r["defenses"] for r in load(path) if r["type"] == "round"] == [["callback", "once_only"]] * 2
