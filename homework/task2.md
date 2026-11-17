# Task 2: AI reviewer replaces the human reviewer

## Console output (one successful run)

```
🛠  generate (attempt 1): The function uses a regex to extract numeric values with their unit letters, converts each to seconds,
sums them, and validates that the whole string is consumed.
❌ test: ValueError: Invalid duration format near ' 1H 30M '
🤔 reflect: - **Why it failed**
  * The loop enforces that each match starts exactly where the previous one ended (`if m.start() != pos`).
    In the test string `" 1H 30M "` there are spaces **between** the

🛠  generate (attempt 2): The function strips the input, then uses a regex that tolerates surrounding whitespace to find number‑unit pairs,
sums their seconds, and finally checks that nothing but whitespace remains; otherwise it raises ValueError.
❌ test: AssertionError: expected ValueError for ''
🤔 reflect: - **Why it failed**
  * The function treats an empty or whitespace‑only string as a valid input and returns `0` (the early‑return block). 
The test suite, however, expects a **`ValueError`** to be ra

🛠  generate (attempt 3): The function now raises ValueError for empty/whitespace strings and otherwise parses numeric‑unit pairs, 
converting each to seconds and summing them; any unmatched characters trigger a ValueError.
✅ test: all tests passed
🔍 reviewer: changes requested (1): Please ensure that fractional values are handled correctly for all units, not just hours. 
Currently minutes and seconds are truncated after conversion (e.g., '1.5m' becomes 60 seconds). Adjust the code so that fractional
minutes and seconds are also converted to the correct total seconds (e.g., '1.5m' should be 90 seconds).

🛠  generate (attempt 4): The function now accumulates seconds as a float, applying the proper factor for hours, minutes,
and seconds, so fractional minutes and seconds are preserved. After validation it rounds the final total and returns it as an int.
✅ test: all tests passed
🔍 reviewer: changes requested (2): The implementation works, but please add a small improvement: handle or explicitly reject
negative duration values (e.g., "-5m") with a clear ValueError message.

────────────────────────────────────────────────────────────
import re

def parse_duration(s: str) -> int:
    """Convert a duration string like '1h30m', '45s' or '2h' to seconds.
    Units (h, m, s) are case‑insensitive and may appear in any order.
    Whitespace between parts is ignored.
    Empty or whitespace‑only strings raise ValueError.
    Invalid formats raise ValueError.
    Fractional values are supported for all units.
    """
    if not s or s.strip() == "":
        raise ValueError("duration string is empty")
    # Match number (int or float) followed by a unit character
    pattern = re.compile(r"\s*(?P<value>\d+(?:\.\d*)?)\s*(?P<unit>[hms])", re.I)
    total_seconds = 0.0
    for m in pattern.finditer(s):
        val = float(m.group('value'))
        unit = m.group('unit').lower()
        if unit == 'h':
            total_seconds += val * 3600
        elif unit == 'm':
            total_seconds += val * 60
        else:  # 's'
            total_seconds += val
    # Any characters left after removing matched parts indicate an error
    leftover = pattern.sub('', s).strip()
    if leftover:
        raise ValueError(f"Invalid duration format near '{leftover}'")
    # Return the total as an integer number of seconds (rounded to nearest)
    return int(round(total_seconds))
────────────────────────────────────────────────────────────
Accept the code? (yes / your feedback) > y

Result: code accepted ✅, attempts: 4
Time: 24s
```

## Notes

**What surprised me.** - First two versions failed on unstated details -the whitespace between parts and the empty string aren't in the task
  text, and TESTS checks them on purpose. But reflect found the cause both times.
 - The reviewer kept moving the goal. Fractions and negative values aren't in the task. This is partly by design,
  because the reviewer prompt says "Always reject the code and ask for one more small improvement."

**Where the model needed a guard in code.** MAX_ATTEMPTS caps the test-fail → reflect → generate loop (at most 2 reflects), 
and review_rejections caps reviewer rejections at 2 before the human step.

