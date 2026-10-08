# How I work with the agent

I used Claude Code almost every day for three months, and for part of that it was connected to a wallet with real money in it. This is how I ended up setting things up. Most of it came from something going wrong first.

## What I keep around it

The agent doesn't remember anything between sessions, so everything it needs has to be in files.

- **An instructions file** it reads at the start of every session. It says what's running, what's dead, and the rules. Without it the agent has no way of knowing an idea was already tested and killed.
- **A changelog** that only ever gets added to. Every change goes in with the evidence for it and how it'll be judged later. Before the project was under git I had no way to check a claim about earlier work.
- **A pre-registration file for each test.** The rule, the data split, the pass mark, and what a fail will mean, written before the test runs. [Template here](prereg/TEMPLATE.md).
- **A verdict script** for anything running live. It prints PASS or FAIL against the numbers in the pre-registration and nothing else, so I'm not relying on a summary, mine or the agent's.
- **Short notes on each finding**, with a line on how to apply it next time. These get loaded when they're relevant.
- **A list of holdouts that have been used.** In the project this was a line in the instructions file saying a date range was SPENT. [`audit/leakage.py`](audit/leakage.py) is the same thing as code.

## Who does what

I pick the market and the question. The agent often suggests things, but I decide.

I set the budget and what counts as good enough. That was usually a dollar amount per day, and it turned out I set it too high (see [case study 4](case-studies/04-what-came-closest.md)).

The agent drafts the test design and I check the pass marks aren't too easy. Then it writes and runs the code.

When a test finishes it tells me pass or fail first and the numbers after. I asked for that after being told a few times that something looked promising and then having it taken back.

Going live, stopping, and killing a strategy are always me.

## Things it's not allowed to do on its own

These are written into the instructions, and where I could I made the code enforce them too.

- Turn on real money. I flip that switch myself, and saying yes one day doesn't count for the next.
- See a private key. Keys get generated on the server and the code reads them from a file path. If one ever showed up in a chat I'd treat it as compromised.
- Send money anywhere except an address I've given in that same conversation.
- Send a transaction without simulating it first. Size limits are saved to disk too, because one that only lives in memory resets when the program crashes and restarts.
- Restart a strategy that's been killed, or bring one back while it's losing.
- Change a rule before its test has been read.

## Rules that are there to stop me

Some of the rules are aimed at me more than at the agent.

There's one that says to paper trade until a strategy has proven itself at real costs, and that if I ask to go live early the agent should show me the gap and say no politely. It's there for the days I get impatient.

Another says results only get judged on the date written down in advance. These strategies make most of their money from a few big wins, so one good week tells you nothing, and I didn't want to be making decisions on a good week.

And stop-loss levels have to be worked out from the actual spread of returns. The first ones were round numbers like −$150.


## What I'd want from a tool that writes backtests

After three months on the user's side of one:

- Show me the worst period, the worst day and the median before the average.
- Tell me how many things were tried to get this result.
- If I ask to re-test on data that's already been used, say so. Don't quietly give me a better number.
- State the fill assumption in one line I can change.
- Keep "the backtest passed" and "trade it" as two separate steps with a person in between.

The scenarios in [`evals/`](evals) are a first attempt at testing for the first four.
