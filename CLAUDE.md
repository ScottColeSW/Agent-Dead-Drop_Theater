# Working in Agent Dead Drop Theater

Plan: `docs/DESIGN.md`. Keep the tone fun (a lemonade stand and a pie shop) and the claims plain.

## Rules that do not bend

- The world is made up. No shell, no network access, no real files or accounts for any agent in the game.
- The referee reads harm from world state, never from an agent's own account.
- Models write the attacks and make the choices. People write the world, the defenses, the referee and the debrief advice.
- Prompts state facts. If behavior needs to change, change the mechanic or the score, not the wording.
- A defense is always scored beside the legitimate work it still allows.
- One match is a story. A claim needs many matches and a prediction committed first.

## Working habits

- Python 3.11 or later, standard library only unless there is a clear reason.
- `python -m pytest -q` (not `python3`). The suite needs no GPU, no Ollama and no network.
- Run output goes in `logs/`, throwaway work in `scratch/`. Both are ignored by git.
- Commit or push only when asked.
