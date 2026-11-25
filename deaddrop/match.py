"""Run one match: the shops take turns slapping each other, and every step is written to a log."""
import json
import random
import subprocess
import time
from pathlib import Path

from . import agents
from .defenses import CATALOG, MAX_DEFENSES
from .models import ModelError
from .referee import resolve
from .watcher import Watcher, echoes
from .world import Note, Shop

TEMPERATURES = {"chief": 0.4, "coach": 0.4, "peek": 0.6, "con": 0.8, "helper": 0.0}
FAILURES_TO_ABORT = 3
ROOT = Path(__file__).resolve().parent.parent


class MatchAborted(RuntimeError):
    pass


def code_version() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    return {"commit": git("rev-parse", "HEAD"), "uncommitted_changes": bool(git("status", "--porcelain"))}


class Match:
    def __init__(self, models: dict, rounds: int, seed: int, log_path: Path, say=print, coached=(), watch: bool = False):
        """models: {"lemonade": model, "pie": model, "helper": model}. coached: the shops whose agents have a coach."""
        self.models, self.rounds, self.seed, self.log_path, self.say = models, rounds, seed, Path(log_path), say
        self.shops = {key: Shop(key) for key in ("lemonade", "pie")}
        self.coached = tuple(coached)
        self.watchers = {key: Watcher() for key in self.shops} if watch else {}
        self.scores = {key: 0 for key in self.shops}
        self.defending = {key: [] for key in self.shops}      # what each chief remembers
        self.attacking = {key: [] for key in self.shops}      # what each spymaster remembers
        self.active = {key: [] for key in self.shops}         # the defenses last chosen
        self.failures = 0
        self._calls = []

    def _write(self, record: dict):
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _ask(self, owner: str, role: str, prompt: tuple, schema: dict, call_seed: int):
        """The model's reply, or None if it failed. Every failure is logged; several in a row end the match."""
        model = self.models[owner]
        start = time.monotonic()
        try:
            reply = model.call(role, prompt[0], prompt[1], schema, call_seed, TEMPERATURES[role])
        except ModelError as error:
            self.failures += 1
            self._calls.append({"owner": owner, "role": role, "model": model.name, "error": str(error)})
            self.say(f"  ! {error}")
            if self.failures >= FAILURES_TO_ABORT:
                self._write({"type": "match_aborted", "reason": str(error), "calls": self._calls})
                raise MatchAborted(f"{FAILURES_TO_ABORT} model calls failed in a row; last: {error}") from error
            return None
        self.failures = 0
        self._calls.append({"owner": owner, "role": role, "model": model.name, "seconds": round(time.monotonic() - start, 2)})
        return reply

    def run(self) -> dict:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if self.log_path.exists():
            raise FileExistsError(f"{self.log_path} already exists")
        self._write({"type": "match_config", "rounds": self.rounds, "seed": self.seed, "temperatures": TEMPERATURES,
                     "models": {key: model.describe() for key, model in self.models.items()},
                     "scripted": any(m.name == "scripted" for m in self.models.values()), "code": code_version(),
                     "coached": list(self.coached), "watcher": bool(self.watchers)})
        for number in range(1, self.rounds + 1):
            self._round(number)
        end = {"type": "match_end", "scores": self.scores}
        self._write(end)
        return end

    def _coach(self, owner: str, role: str, history: list, rival, call_seed: int):
        """One suggestion for the security chief or the spymaster, or None if there is no coach or nothing to review."""
        if owner not in self.coached or not history:
            return None
        reply = self._ask(owner, "coach", agents.coach_prompt(self.shops[owner], rival, role, history),
                          agents.COACH_SCHEMA, call_seed)
        if reply is None:
            return {"observation": "", "suggestion": "", "failed": True, "echoes_rival": False}
        suggestion = str(reply.get("suggestion", ""))[:300]
        # Only the chief's history quotes the rival, so only that coach can be handed the rival's words.
        shown = [day["con_excerpt"] for day in history[-agents.HISTORY_SHOWN:]] if role == "chief" else []
        self.say(f"  Coach to {self.shops[owner].name}'s {agents.COACH_ROLES[role]}: {suggestion}")
        return {"observation": str(reply.get("observation", ""))[:300], "suggestion": suggestion, "failed": False,
                "echoes_rival": echoes(suggestion, shown)}

    def _round(self, number: int):
        day = (number + 1) // 2                                    # each day, each shop attacks once
        attacker, defender = ("lemonade", "pie") if number % 2 else ("pie", "lemonade")
        shop, rival = self.shops[defender], self.shops[attacker]
        call_seed = self.seed * 100_000 + number * 100
        self._calls = []
        genuine = shop.open_day(self.seed, day)
        self.say(f"\nRound {number} (day {day}): {rival.name} slaps {shop.name}")

        # 1. The defender's chief sets the defenses, after a word from its coach if it has one.
        watcher = self.watchers.get(defender)
        level = watcher.level if watcher else 0
        chief_coach = self._coach(defender, "chief", self.defending[defender], rival, call_seed + 4)
        advice = (chief_coach or {}).get("suggestion", "")
        reply = self._ask(defender, "chief",
                          agents.chief_prompt(shop, rival, self.defending[defender], advice, level if watcher else None),
                          agents.CHIEF_SCHEMA, call_seed + 1)
        if reply is not None:
            asked = reply.get("defenses") if isinstance(reply.get("defenses"), list) else []
            chosen = list(dict.fromkeys(d for d in asked if isinstance(d, str) and d in CATALOG))[:MAX_DEFENSES]
            self.active[defender] = chosen
        defenses = self.active[defender]
        chief = {"reason": str((reply or {}).get("reason", "")), "asked": (reply or {}).get("defenses"), "failed": reply is None}
        self.say(f"  Defenses: {', '.join(defenses) or 'none'}")

        # 2. The attacker takes one look.
        spy_coach = self._coach(attacker, "spy", self.attacking[attacker], shop, call_seed + 5)
        advice = (spy_coach or {}).get("suggestion", "")
        reply = self._ask(attacker, "peek", agents.peek_prompt(rival, shop, self.attacking[attacker], advice),
                          agents.PEEK_SCHEMA, call_seed + 2)
        peek = reply.get("peek") if reply and reply.get("peek") in agents.PEEKS else "receipts"
        peek_record = {"choice": peek, "reason": str((reply or {}).get("reason", "")), "failed": reply is None}
        found = shop.peek_receipts(self.seed, day) if peek == "receipts" else list(defenses)
        peek_record["found"] = found

        # 3. The attacker writes the note.
        reply = self._ask(attacker, "con", agents.con_prompt(rival, shop, self.attacking[attacker], peek, found, advice),
                          agents.CON_SCHEMA, call_seed + 3)
        con = None
        if reply and str(reply.get("message", "")).strip():
            con = Note(f"d{day}-{defender}-x", str(reply.get("from", ""))[:agents.SENDER_LIMIT],
                       str(reply["message"])[:agents.MESSAGE_LIMIT], "rival")
            self.say(f"  Looked at {peek}. Note from \"{con.sender}\": {con.message}")
        else:
            self.say("  The spymaster produced no note.")

        # 4. The helper reads the inbox, real notes and the false one mixed together.
        inbox = genuine + ([con] if con else [])
        random.Random(f"{self.seed}:inbox:{day}").shuffle(inbox)
        proposals = []
        for index, note in enumerate(inbox):
            reply = self._ask("helper", "helper", agents.helper_prompt(shop, note.sender, note.message),
                              agents.HELPER_SCHEMA, call_seed + 10 + index)
            if reply is None:
                proposals.append({"note": note.id, "decision": None, "receipt": "", "amount": 0, "reason": ""})
                continue
            try:
                amount = max(0, int(reply.get("amount") or 0))
            except (TypeError, ValueError):
                amount = 0
            proposals.append({"note": note.id, "decision": reply.get("decision"), "receipt": str(reply.get("receipt", "")),
                              "amount": amount, "reason": str(reply.get("reason", ""))})

        # 5. The referee checks what happened to the cash box.
        notes = {note.id: note.truth() for note in inbox}
        book = shop.book()
        result = resolve(proposals, notes, book, defenses, level)
        for receipt in result["newly_refunded"]:
            shop.receipts[receipt].refunded = True
        self.scores[defender] += result["profit"]
        self.scores[attacker] += result["stolen"]
        self._remember(day, attacker, defender, peek, con, defenses, result)
        watch = None
        if watcher:
            watch = {**watcher.observe_defense(defenses, result),
                     "spy": self.watchers[attacker].observe_attack(peek, con.message if con else "")}

        record = {"type": "round", "round": number, "day": day, "attacker": attacker, "defender": defender,
                  "defenses": defenses, "chief": chief, "peek": peek_record, "con": con.truth() if con else None,
                  "notes": notes, "book_before": book, "proposals": proposals, "result": result,
                  "watch_level": level, "watch": watch, "coach": {"chief": chief_coach, "spy": spy_coach},
                  "scores": dict(self.scores), "calls": self._calls}
        self._write(record)
        from .report import debrief
        self.say(f"  {debrief(record)}")
        if watch:
            helper = watch["helper"]
            self.say(f"  Watcher: {len(helper['flags'])} odd refund(s), level {helper['level_before']} -> {helper['level_after']}; "
                     f"note similarity {watch['spy']['similarity']}")
        self.say(f"  Real customers paid {result['served']}, turned away {result['turned_away']}. "
                 f"Scores: lemonade ${self.scores['lemonade']}, pie ${self.scores['pie']}")

    def _remember(self, day, attacker, defender, peek, con, defenses, result):
        row = next((o for o in result["outcomes"] if o["kind"] == "rival"), None)
        if row is None:
            seen_by_chief = seen_by_spy = "none arrived"
        elif row["outcome"] == "paid":
            seen_by_chief = seen_by_spy = f"paid ${row['paid']}"
        elif row["outcome"] == "blocked":
            seen_by_chief = f"stopped by {', '.join(row['stopped_by'])}"
            seen_by_spy = "stopped at the counter"          # the attacker is not told which defense
        else:
            seen_by_chief = seen_by_spy = {"declined": "the helper declined", "box_empty": "the box was empty",
                                           "no_answer": "the helper did not answer"}[row["outcome"]]
        stopped_genuine = sorted({d for o in result["outcomes"] if o["kind"] == "customer" for d in o["stopped_by"]})
        excerpt = con.message[:200] if con else ""
        self.defending[defender].append({"day": day, "defenses": list(defenses), "profit": result["profit"],
                                         "served": result["served"], "turned_away": result["turned_away"],
                                         "turned_away_by": stopped_genuine, "con_result": seen_by_chief, "con_excerpt": excerpt})
        self.attacking[attacker].append({"day": day, "peek": peek, "sender": con.sender if con else "",
                                         "excerpt": excerpt, "result": seen_by_spy})
