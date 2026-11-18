# Task 3: Checkpoints and time travel

## Console output (one successful run)

```
$ python homework/task3.py run

🛠  generate (attempt 1): The function uses a regex to find all number‑unit pairs (h, m, s), converts each to seconds, and sums them.
❌ test: AssertionError: expected ValueError for ''
🤔 reflect: - **Why it failed:**
  - The function returns `0` for an empty string because `re.findall` yields no matches and the loop never runs. The test expects a **`ValueError`** to be raised for an empty (o

🛠  generate (attempt 2): The function lower‑cases the input, validates that the whole string consists of one or more <number><unit> groups (h, m, s) using fullmatch, raises ValueError otherwise, then sums the seconds for each group.
❌ test: ValueError
🤔 reflect: - **Too‑strict validation** – the pattern `r'(?:\d+[hms])+'` only matches a *continuous* string of digit‑unit pairs. Test inputs that contain spaces (e.g., `"1h 30m"`), leading/trailing whitespace, or

🛠  generate (attempt 3): The function trims whitespace, validates that the string consists of digit‑unit pairs possibly separated by spaces, then sums each component converting hours and minutes to seconds.
✅ test: all tests passed
Result: attempts = 3 | error = False
Time: 7s
```

## Replay: time travel from the first failed test

```
$ python homework/task3.py replay

step | next            | attempts | error
  -1 | ('__start__',)  | None | False
   0 | ('generate',)   | 0 | False
   1 | ('test',)       | 1 | False
   2 | ('reflect',)    | 1 | True
   3 | ('generate',)   | 1 | True
   4 | ('test',)       | 2 | True
   5 | ('reflect',)    | 2 | True
   6 | ('generate',)   | 2 | True
   7 | ('test',)       | 3 | True
   8 | ('human_review',) | 3 | False
   9 | ()              | 3 | False

Going back to step 2 (first failed test)
🤔 reflect: - **Why it failed:**
  - The function returns `0` for an empty string because `re.findall` yields no matches, leaving `total` at its initial value. The test expects a **`ValueError`** to be raised f

🛠  generate (attempt 2): The function lower‑cases and trims the input, uses a full‑match regex to ensure the whole string consists of one or more <number><unit> blocks, raises ValueError otherwise, then sums each block converting hours and minutes to seconds.
❌ test: ValueError
🤔 reflect: - **Too‑strict pattern** – the `fullmatch` regex `r'(?:\d+[hms])+'` only accepts a compact string like `1h30m`. Test cases that contain spaces (e.g., `"1h 30m"`), tabs, or other whitespace between the

🛠  generate (attempt 3): The regex now allows optional whitespace between number‑unit pairs, so inputs like "1h 30m" are accepted; the rest of the logic unchanged computes total seconds.
✅ test: all tests passed
Result: attempts = 3 | error = False

Final code:
import re
def parse_duration(s: str) -> int:
    s = s.lower().strip()
    if not re.fullmatch(r'(?:\d+\s*[hms]\s*)+', s):
        raise ValueError
    total = 0
    for v, u in re.findall(r'(\d+)\s*([hms])', s):
        v = int(v)
        total += v * 3600 if u == 'h' else v * 60 if u == 'm' else v
    return total
Time: 6s
```

## Notes
**What surprised me.**
A pause is also a checkpoint (human_review);
The original history survives the replay. update_state adds a branch, and the first run's checkpoints stay in task3.db
**Where the model needed a guard in code.**

| Guard | What it protects against |
|---|---|
| `recursion_limit: 50` in `CFG` | The graph looping forever. LangGraph raises `GraphRecursionError` at 50 steps. |
| `os.path.exists(DB)` before `os.remove` | `FileNotFoundError` on the first run, when `task3.db` doesn't exist. |
| `sys.argv[1:] == ["run"]` | Deleting the database on any command other than `run`. `replay` needs the saved history. |
| `next(..., None)` and `sys.exit("No failed test in history...")` | `replay` when the history has no failed test, for example before you've run `run`. The script exits with a clear message. |
| `while "__interrupt__" in result` with `resume="yes"` | The graph blocking on `human_review` with nobody to answer. It auto-accepts. |


