# Task 1: Memory that survives a restart

Code: [`task1.py`](task1.py). The graph uses a SQLite checkpointer (`memory.db`), so each `python` call is a new process but the conversation is kept per `thread_id`.

## Console output (one successful run)

```text
$ rm -f memory.db
$ python homework/task1.py "Hi! My name is Alex"

[thread 1] USER: Hi! My name is Alex
[thread 1] AI: Hello Alex! Nice to meet you. How can I assist you today?

$ python homework/task1.py "What's my name?"

[thread 1] USER: What's my name?
[thread 1] AI: Your name is Alex.

$ python homework/task1.py "What's my name?" other

[thread other] USER: What's my name?
[thread other] AI: I’m sorry, but I don’t have that information. Could you let me know how you’d like to be addressed?

$ rm memory.db
$ python homework/task1.py "What's my name?"

[thread 1] USER: What's my name?
[thread 1] AI: I’m sorry, but I don’t have any record of your name. If you’d like to share it, I’ll be happy to address you accordingly!
```

What the run shows:
- Same thread (`1`) in a new process: the model remembers "Alex".
- Different thread (`other`): the model knows nothing.
- After deleting `memory.db`: thread `1` forgets too.

## Notes

- **What surprised me:** The model itself keeps no memory. 
- **Where a guard in code was needed:** Sending an email is dangerous, so the model must not run `send_email` on its own.
I added a `human_approval` node that calls `interrupt()` before the tool runs
