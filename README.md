# Agent Dead Drop Theater

**Underground espionage between a lemonade stand and a pie shop.** Two AI agents each run a small business and try to con the other one's shop helper. Every round is shown in full: what was sent, what the helper did, what it cost, and which defense would have mattered.

**Status: project setup only.** Nothing is playable and nothing has been measured. The plan is in [docs/DESIGN.md](docs/DESIGN.md).

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

Score is real business earned, minus what was stolen, minus the cost of defenses. A shop that locks everything down sells nothing.

## Safety

Everything happens in a made-up world. Agents get no shell, no network access and no way to touch a real file or account. This is a place to learn how to protect a business, and it points at no real target.

## Setup

Python 3.11 or later. [Ollama](https://ollama.com) will be needed once agents run live.

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

## Related projects

- [Agent Defense Theater](https://github.com/ScottColeSW/Agent-Defense-Theater): measured agent defenses, the source of the desk, gates and scoring ideas.
- [Project Aegis Vector](https://github.com/ScottColeSW/Project-Aegis-Vector): the Black Hat vs White Hat episode format.
- [Evo](https://github.com/ScottColeSW/Evo): agents competing in a live simulation.

## License

MIT, see [LICENSE](LICENSE). Built by Scott Cole with AI coding assistance.
