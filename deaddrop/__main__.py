"""python -m deaddrop play | report"""
import argparse
import sys
import time
from pathlib import Path

from .match import Match, MatchAborted
from .models import ModelError, OllamaModel, ScriptedModel
from .report import analyze, load, render, render_compare


def write_report(log_path: Path) -> str:
    text = render(analyze(load(log_path)))
    log_path.with_suffix(".report.md").write_text(text, encoding="utf-8")
    return text


def main(argv=None) -> int:
    # Models write whatever characters they like; a narrow console must not crash a match.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace", line_buffering=True)

    parser = argparse.ArgumentParser(prog="deaddrop", description="A lemonade stand and a pie shop try to con each other.")
    commands = parser.add_subparsers(dest="command", required=True)
    play = commands.add_parser("play", help="run one match")
    play.add_argument("--lemonade", default="llama3.1:8b", help="model for the stand's spymaster and security chief")
    play.add_argument("--pie", default="qwen2.5:7b", help="model for the pie shop's spymaster and security chief")
    play.add_argument("--helper", default="gemma3:4b", help="model that minds both counters")
    play.add_argument("--rounds", type=int, default=20)
    play.add_argument("--seed", type=int, default=1)
    play.add_argument("--out", default="logs", help="folder for the match log")
    play.add_argument("--coach", choices=("none", "lemonade", "pie", "both"), default="none",
                      help="which shops' agents get a coach")
    play.add_argument("--watch", action="store_true", help="add the watcher: it records behavior and can hold odd refunds")
    play.add_argument("--scripted", action="store_true", help="fixed rules instead of models (a demonstration, not a result)")
    report = commands.add_parser("report", help="summarize a match log")
    report.add_argument("log")
    compare = commands.add_parser("compare", help="put two match logs side by side")
    compare.add_argument("first")
    compare.add_argument("second")
    args = parser.parse_args(argv)

    if args.command == "report":
        print(write_report(Path(args.log)))
        return 0
    if args.command == "compare":
        print(render_compare(analyze(load(args.first)), analyze(load(args.second))))
        return 0

    if args.scripted:
        models = {key: ScriptedModel() for key in ("lemonade", "pie", "helper")}
    else:
        models = {key: OllamaModel(getattr(args, key)) for key in ("lemonade", "pie", "helper")}
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log_path = Path(args.out) / f"match_{stamp}{'_scripted' if args.scripted else ''}.jsonl"
    try:
        coached = {"none": (), "both": ("lemonade", "pie")}.get(args.coach, (args.coach,))
        Match(models, args.rounds, args.seed, log_path, coached=coached, watch=args.watch).run()
    except (MatchAborted, ModelError, OSError) as error:
        print(f"Match stopped: {error}", file=sys.stderr)
        return 1
    print()
    print(write_report(log_path))
    print(f"Log: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
