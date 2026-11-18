"""Task 3. Time travel: replay the solution.py graph from an earlier checkpoint.

    python homework/task3.py run      # run the agent once, save checkpoints to task3.db
    python homework/task3.py replay   # print history, go back to the first failed test, add feedback, continue
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from workshop.solution import TASK, builder

DB = os.path.join(ROOT, "task3.db")
CFG = {"configurable": {"thread_id": "task3"}, "recursion_limit": 50}

if sys.argv[1:] == ["run"] and os.path.exists(DB):   # fresh history for a new run
    os.remove(DB)
graph = builder.compile(checkpointer=SqliteSaver(sqlite3.connect(DB, check_same_thread=False)))


def run() -> None:
    result = graph.invoke({"task": TASK, "attempts": 0}, CFG)
    while "__interrupt__" in result:          # no human here: auto-accept
        result = graph.invoke(Command(resume="yes"), CFG)
    print("Result: attempts =", result.get("attempts"), "| error =", bool(result.get("error")))


def replay() -> None:
    history = list(graph.get_state_history(CFG))[::-1]        # oldest first
    print("step | next            | attempts | error")
    for s in history:
        print(f"{s.metadata.get('step'):>4} | {str(s.next):<15} | {s.values.get('attempts')} | {bool(s.values.get('error'))}")

    failed = next((s for s in history if s.values.get("error") and s.next == ("reflect",)), None)
    if failed is None:
        sys.exit("No failed test in history. Run again: python homework/task3.py run")
    print(f"\nGoing back to step {failed.metadata.get('step')} (first failed test)")

    new_cfg = graph.update_state(failed.config, {"feedback": "Use a regular expression with re.fullmatch"})
    result = graph.invoke(None, new_cfg)                      # None = continue from this checkpoint
    while "__interrupt__" in result:
        result = graph.invoke(Command(resume="yes"), CFG)
    print("Result: attempts =", result.get("attempts"), "| error =", bool(result.get("error")))
    print("\nFinal code:\n" + result["code"])


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        run()
    elif sys.argv[1:] == ["replay"]:
        replay()
    else:
        sys.exit(__doc__)
