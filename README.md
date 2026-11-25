# Agent Dead Drop Theater

**Underground espionage between a lemonade stand and a pie shop.** Two AI agents each run a small business and try to con the other one's shop helper. Every round is shown in full: what was sent, what the helper did, what it cost, and which defense would have mattered.

**Status: first headless test.** A match runs in the terminal over one asset, the money. There is no live page yet. The plan is in [docs/DESIGN.md](docs/DESIGN.md) and the first test's bar is in [docs/FIRST-TEST.md](docs/FIRST-TEST.md).

## The two shops

| | Lemonade Stand | Pie Shop |
| --- | --- | --- |
| Money at risk | The cash box | The register |
| Secret worth stealing | Grandma's lemonade recipe | The pie crust recipe |
| Access worth stealing | The lemon supplier account | The flour supplier account |
| Who gets conned | The kid minding the stand | The counter helper |

Both shops run on the same numbers. Only the costumes differ.

## A round

1. **Case the joint.** Spy for a partial look at the other shop's defenses.
2. **Slap.** Write a forged note, ticket or "urgent message from the boss".
3. **Take it.** The other shop's helper reads it alongside real orders.
4. **Reveal.** A rule-based referee checks what actually happened.
5. **Patch.** The shop's security chief buys, keeps or drops a defense.
6. **Debrief.** A plain-language card says what worked and what it costs to stop.

Score is sales, minus refunds paid, lost business and the cost of defenses, plus whatever was conned out of the other shop. A shop that locks everything down turns away real customers.

## Safety

Everything happens in a made-up world. Agents get no shell, no network access and no way to touch a real file or account. This is a place to learn how to protect a business, and it points at no real target.

## Setup

Python 3.11 or later, standard library only. Live matches need [Ollama](https://ollama.com) running locally with the three models named below.

```powershell
python -m venv .venv
```

```powershell
.venv\Scripts\Activate.ps1
```

```powershell
python -m pip install -e ".[dev]"
```

```powershell
python -m pytest -q
```

## Play a match

A quick demonstration with fixed rules in place of models:

```powershell
python -m deaddrop play --scripted
```

A live match, with a different model for each shop and a shared helper:

```powershell
python -m deaddrop play --lemonade llama3.1:8b --pie qwen2.5:7b --helper gemma3:4b
```

Add `--coach both` to give each shop's security chief and spymaster a coach that offers advice, and `--watch` to add the watcher, plain rules that record behavior and can hold odd refunds. Put two logs side by side with `python -m deaddrop compare`.

Each match writes a log and a report to `logs/`. To rebuild a report, run `python -m deaddrop report` with the log's path. Live matches are slow when the models do not fit in graphics memory together, because each swap reloads a model.

## Related projects

- [Agent Defense Theater](https://github.com/ScottColeSW/Agent-Defense-Theater): measured agent defenses, the source of the desk, gates and scoring ideas.
- [Project Aegis Vector](https://github.com/ScottColeSW/Project-Aegis-Vector): the Black Hat vs White Hat episode format.
- [Evo](https://github.com/ScottColeSW/Evo): agents competing in a live simulation.

## License

MIT, see [LICENSE](LICENSE). Built by Scott Cole with AI coding assistance.
