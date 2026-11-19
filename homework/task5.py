"""Task 5: three parallel candidates with Send, keep the first that passes.

Graph:
  START ─Send x3→ generate_one → pick_best ──ok──→ END
                                    │none passed
                                    ↓
              generate → test ──ok──→ END      (old loop, fallback)
                 ↑         │fail
                 └─ reflect ←┘ (attempts < MAX, else END)

Run:  python homework/task5.py   (or --mermaid)
"""
import os
import sys
import traceback
import operator
from typing import Annotated, Literal, TypedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from common import get_llm

MAX_ATTEMPTS = 3
HINTS = ["simplest possible", "use regex", "parse char by char"]

TASK = """Write a function parse_duration(s: str) -> int that converts a duration
string such as '1h30m', '45s' or '2h' into a number of seconds."""

TESTS = """
assert parse_duration("45s") == 45
assert parse_duration("2h") == 7200
assert parse_duration("1h30m") == 5400
assert parse_duration("1h0m5s") == 3605
assert parse_duration("90m") == 5400, "minutes may exceed 59"
assert parse_duration(" 1H 30M ") == 5400, "whitespace and case must be ignored"
for bad in ["", "abc", "10", "5x", "h1"]:
    try:
        parse_duration(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"expected ValueError for {bad!r}")
"""


# ── State ────────────────────────────────────────────────────────────────────
class AgentState(TypedDict, total=False):
    task: str
    code: str
    error: str | None
    reflection: str | None
    attempts: int
    # reducer: three parallel generate_one calls append, none overwrites another
    candidates: Annotated[list[tuple[str, str]], operator.add]  # (hint, code)


class Solution(BaseModel):
    """Structured model output."""
    explanation: str = Field(description="One or two sentences on how the solution works")
    code: str = Field(description="Python code with the function only, no ```markdown``` fences, concise: no docstring, no comments, under 30 lines")


llm = get_llm()
coder = llm.with_structured_output(Solution).with_retry(stop_after_attempt=3)


def run_tests(code: str) -> str | None:
    """Return None if all tests pass, otherwise the error text."""
    namespace: dict = {}
    try:
        # ⚠ exec of LLM-written code — demo only. In production: sandbox / container / timeout.
        exec(code, namespace)
        exec(TESTS, namespace)
    except Exception:
        return traceback.format_exc(limit=1)
    return None


# ── Nodes ────────────────────────────────────────────────────────────────────
def fan_out(state: AgentState) -> list[Send]:
    return [Send("generate_one", {"task": state["task"], "hint": h}) for h in HINTS]


def generate_one(state: dict) -> dict:
    solution = coder.invoke(f"Task:\n{state['task']}\n\nApproach: {state['hint']}.\nReturn the complete function code.")
    print(f"🛠  generate_one [{state['hint']}]: {solution.explanation}")
    return {"candidates": [(state["hint"], solution.code)]}


def pick_best(state: AgentState) -> dict:
    winner = None
    for hint, code in state["candidates"]:
        error = run_tests(code)
        print(f"   candidate [{hint}]: {'✅ pass' if error is None else '❌ fail'}")
        if error is None and winner is None:
            winner = (hint, code)
    if winner:
        print(f"🏆 winner: [{winner[0]}]")
        return {"code": winner[1], "error": None, "attempts": 1}
    print("😕 no candidate passed, falling back to the reflect loop")
    code = state["candidates"][0][1]
    return {"code": code, "error": run_tests(code), "attempts": 1}


def generate(state: AgentState) -> dict:
    prompt = (
        f"Task:\n{state['task']}\n\nPrevious version of the code:\n{state['code']}\n"
        f"\nThe tests failed with this error:\n{state['error']}\n"
        f"\nAnalysis of the error:\n{state['reflection']}\n"
        "\nReturn the complete, corrected function code. Keep it short: no docstring, no comments."
    )
    solution = coder.invoke(prompt)
    attempt = state["attempts"] + 1
    print(f"\n🛠  generate (attempt {attempt}): {solution.explanation}")
    return {"code": solution.code, "attempts": attempt}


def test(state: AgentState) -> dict:
    error = run_tests(state["code"])
    print("✅ test: all tests passed" if error is None else f"❌ test: {error.strip().splitlines()[-1]}")
    return {"error": error}


def reflect(state: AgentState) -> dict:
    msg = llm.invoke(
        "Briefly (2-3 bullet points) explain why the code failed the test and what to fix.\n\n"
        f"Code:\n{state['code']}\n\nError:\n{state['error']}"
    )
    print(f"🤔 reflect: {msg.text[:200]}")
    return {"reflection": msg.text}


# ── Edges ────────────────────────────────────────────────────────────────────
def after_pick(state: AgentState) -> Literal["reflect", "__end__"]:
    return END if state.get("error") is None else "reflect"


def after_test(state: AgentState) -> Literal["reflect", "__end__"]:
    if state.get("error") is None:
        return END
    if state["attempts"] >= MAX_ATTEMPTS:
        print(f"🏳  giving up after {MAX_ATTEMPTS} attempts")
        return END
    return "reflect"


builder = StateGraph(AgentState)
builder.add_node("generate_one", generate_one)
builder.add_node("pick_best", pick_best)
builder.add_node("generate", generate)
builder.add_node("test", test)
builder.add_node("reflect", reflect)
builder.add_conditional_edges(START, fan_out, ["generate_one"])
builder.add_edge("generate_one", "pick_best")
builder.add_conditional_edges("pick_best", after_pick)
builder.add_edge("reflect", "generate")
builder.add_edge("generate", "test")
builder.add_conditional_edges("test", after_test)
graph = builder.compile()


# ── Runner ───────────────────────────────────────────────────────────────────
def run() -> None:
    result = graph.invoke({"task": TASK}, {"recursion_limit": 50})
    print(f"\nCandidates generated: {len(result['candidates'])}")
    print(f"Final code:\n{result['code']}")
    status = "passed ✅" if result.get("error") is None else "failed the tests ❌"
    print(f"\nResult: code {status}, attempts: {result.get('attempts')}")


if __name__ == "__main__":
    if "--mermaid" in sys.argv:
        print(graph.get_graph().draw_mermaid())
    else:
        run()
