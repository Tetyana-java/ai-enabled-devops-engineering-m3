# Task 5: Parallel candidates with Send

## Console output (one successful run)

```
$ python homework/task5.py

🛠  generate_one [simplest possible]: The function uses a regex to find all number‑unit pairs (h, m, s), converts each to seconds, and sums them.
🛠  generate_one [use regex]: The function finds all number‑unit pairs (h, m, s) with regex, converts each to seconds, and sums them.
🛠  generate_one [parse char by char]: The function accumulates digits into a number, then when a unit character (h,m,s) appears it multiplies the number by the unit's seconds and adds to total.
   candidate [simplest possible]: ❌ fail
   candidate [use regex]: ❌ fail
   candidate [parse char by char]: ❌ fail
😕 no candidate passed, falling back to the reflect loop
🤔 reflect: - **Why it failed:**
  - The function silently returns `0` when the input string contains no time tokens (e.g., an empty string). The test suite expects a **`ValueError`** for such invalid input, so

🛠  generate (attempt 2): The function validates the input, extracts number‑unit pairs, ensures the whole string matches the pattern, and converts each part to seconds, raising ValueError for empty or malformed strings.
❌ test: ValueError
🤔 reflect: - **Over‑strict validation** – after extracting the `(number)(unit)` pairs the code builds `''.join(v+u …)` and compares it to the original string. Any harmless characters (e.g., spaces, commas, or up

🛠  generate (attempt 3): The function strips all whitespace, lower‑cases the string, ensures the whole string matches a sequence of number‑unit pairs, then sums each part converted to seconds.
✅ test: all tests passed

Candidates generated: 3
Final code:
import re
def parse_duration(s: str) -> int:
    if not s:
        raise ValueError
    s = re.sub(r'\s+', '', s).lower()
    if not re.fullmatch(r'(?:\d+[hms])+$', s):
        raise ValueError
    total = 0
    for v, u in re.findall(r'(\d+)([hms])', s):
        total += int(v) * (3600 if u == 'h' else 60 if u == 'm' else 1)
    return total

Result: code passed ✅, attempts: 3
Time: 7s
```

## Notes
**What surprised me.**
All three parallel candidates failed, even though the hints differ. The "simplest possible" and "use regex" candidates were nearly identical,
so the hints gave less variety than I expected. The fallback loop saved the run: it needed two reflect rounds, and the second round passed on the last allowed attempt.

**Where the model needed a guard in code.**

| Guard | What it protects against |
|---|---|
| `candidates: Annotated[..., operator.add]` | Three parallel `generate_one` calls overwriting each other's result. The reducer appends instead. |
| `pick_best` returns `candidates[0]` with `attempts: 1` when all candidates fail | The retry loop having no code to repair. It starts from the first candidate with a counter already set |
| `MAX_ATTEMPTS = 3` in `after_test` | The reflect/generate/test loop running forever. |
| `recursion_limit: 50` in `run()` | `GraphRecursionError` instead of an endless loop if the counter logic breaks. (networking, rate limiter) |
| `try/except` around `exec` in `run_tests` | Model-written code that crashes or has a syntax error. . |
