"""Task 2: AI reviewer replaces the human reviewer (human only after 2 rejections).

Graph:
  START → generate → test ──ok──→ reviewer ──approved──→ END
              ↑          │fail        │rejected (1st)──→ generate
              └─ reflect ←┘           │rejected (2nd)──→ human_review → END / generate

The tests DELIBERATELY demand a bit more than the task says (whitespace, case, errors),
so the self-correction loop almost certainly kicks in at least once.

Run:  python homework/task2.py   (or --mermaid)
"""
import os
import sys
import traceback
from typing import Literal, TypedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from common import get_llm

MAX_ATTEMPTS = 3

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
    feedback: str | None      # comment from the reviewer
    approved: bool
    review_rejections: int
    attempts: int


class Solution(BaseModel):
    """Structured model output."""
    explanation: str = Field(description="One or two sentences on how the solution works")
    code: str = Field(description="Python code with the function only, no ```markdown``` fences, under 40 lines")


class Review(BaseModel):
    approved: bool = Field(description="True only if the code fully meets the task and the rules")
    comments: str = Field(description="What must be changed; empty if approved")


llm = get_llm()
review_llm = llm.with_structured_output(Review, method="json_schema").with_retry(stop_after_attempt=3)
# retry: providers occasionally return malformed structured output (e.g. long code breaks the JSON)
coder = llm.with_structured_output(Solution).with_retry(stop_after_attempt=3)


# ── Nodes ────────────────────────────────────────────────────────────────────
def generate(state: AgentState) -> dict:
    prompt = f"Task:\n{state['task']}\n"
    if state.get("code"):
        prompt += f"\nPrevious version of the code:\n{state['code']}\n"
    if state.get("error"):
        prompt += f"\nThe tests failed with this error:\n{state['error']}\n"
    if state.get("reflection"):
        prompt += f"\nAnalysis of the error:\n{state['reflection']}\n"
    if state.get("feedback"):
        prompt += f"\nComment from the reviewer:\n{state['feedback']}\n"
    prompt += "\nReturn the complete, corrected function code. Follow the reviewer comments, if any."

    solution = coder.invoke(prompt)
    attempt = state.get("attempts", 0) + 1
    print(f"\n🛠  generate (attempt {attempt}): {solution.explanation}")
    return {"code": solution.code, "attempts": attempt, "feedback": None}


def test(state: AgentState) -> dict:
    namespace: dict = {}
    try:
        # ⚠️ exec of LLM-written code — demo only. In production: sandbox / container / timeout.
        exec(state["code"], namespace)
        exec(TESTS, namespace)
    except Exception:
        err = traceback.format_exc(limit=1)
        print(f"❌ test: {err.strip().splitlines()[-1]}")
        return {"error": err}
    print("✅ test: all tests passed")
    return {"error": None}


def reflect(state: AgentState) -> dict:
    msg = llm.invoke(
        "Briefly (2-3 bullet points) explain why the code failed the test and what to fix.\n\n"
        f"Code:\n{state['code']}\n\nError:\n{state['error']}"
    )
    print(f"🤔 reflect: {msg.text[:200]}")
    return {"reflection": msg.text}


def reviewer(state: AgentState) -> dict:
    review = review_llm.invoke(
        "You are a reviewer. Always reject the code (approved=false) and ask for one more small improvement.\n\n"
        f"Task:\n{state['task']}\n\nCode:\n{state['code']}"
    )
    if review.approved:
        print("🔍 reviewer: approved")
        return {"approved": True}
    n = state.get("review_rejections", 0) + 1
    print(f"🔍 reviewer: changes requested ({n}): {review.comments}")
    return {"approved": False, "review_rejections": n, "feedback": review.comments,
            "error": None, "reflection": None}


def human_review(state: AgentState) -> Command[Literal["generate", "__end__"]]:
    answer = interrupt({"code": state["code"], "question": "Accept the code? (yes / your feedback)"})
    if str(answer).strip().lower() in {"yes", "y"}:
        return Command(goto=END)
    return Command(goto="generate", update={"feedback": answer, "error": None, "reflection": None, "review_rejections": 0})


# ── Edges ────────────────────────────────────────────────────────────────────
def after_review(state: AgentState) -> Literal["generate", "human_review", "__end__"]:
    if state.get("approved"):
        return END
    return "human_review" if state.get("review_rejections", 0) >= 2 else "generate"


def after_test(state: AgentState) -> Literal["reviewer", "reflect", "__end__"]:
    if state.get("error") is None:
        return "reviewer"
    if state.get("attempts", 0) >= MAX_ATTEMPTS:
        print(f"🏳  giving up after {MAX_ATTEMPTS} attempts")
        return END
    return "reflect"


builder = StateGraph(AgentState)
builder.add_node("generate", generate)
builder.add_node("test", test)
builder.add_node("reflect", reflect)
builder.add_node("reviewer", reviewer)
builder.add_node("human_review", human_review)
builder.add_edge(START, "generate")
builder.add_edge("generate", "test")
builder.add_conditional_edges("test", after_test)
builder.add_conditional_edges("reviewer", after_review)
builder.add_edge("reflect", "generate")
graph = builder.compile(checkpointer=InMemorySaver())


# ── Runner ───────────────────────────────────────────────────────────────────
def run() -> None:
    cfg = {"configurable": {"thread_id": "workshop-1"}, "recursion_limit": 50}
    result = graph.invoke({"task": TASK, "attempts": 0, "review_rejections": 0}, cfg)
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("\n" + "─" * 60 + f"\n{payload['code']}\n" + "─" * 60)
        answer = input(f"{payload['question']} > ")
        result = graph.invoke(Command(resume=answer), cfg)

    status = "accepted ✅" if result.get("error") is None else "failed the tests ❌"
    print(f"\nResult: code {status}, attempts: {result.get('attempts')}")


if __name__ == "__main__":
    if "--mermaid" in sys.argv:
        print(graph.get_graph().draw_mermaid())
    else:
        run()
