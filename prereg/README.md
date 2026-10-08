# Pre-registrations

Before each test there's a short file with the rule, the data split and the pass mark. The agent drafted them from what I'd asked for (a couple of them quote me as "User"), and I checked the pass marks before anything ran. These four are copied unchanged from the private repo. The commit hashes are from that repo, and times are UTC+8.

| File | Written and committed | Result committed | Outcome |
|---|---|---|---|
| [`FS1-funding-settlement-snipe.md`](FS1-funding-settlement-snipe.md) | `4e598f3`, 6 Oct 23:43, before pulling the data | `64544f1`, 7 Oct 00:50 | Fail |
| [`LLM1-llm-forecast-vs-price.md`](LLM1-llm-forecast-vs-price.md) | `813be9d`, 7 Oct 16:38. Amended at 16:54 and 17:21, before reading the forecasts | `dbd9877`, 7 Oct 17:29 | Fail |
| [`WCLEAN1-clean-wallet-filter.md`](WCLEAN1-clean-wallet-filter.md) | `5bb9b86`, 7 Oct 22:11, before any filtered numbers | `8225689`, 7 Oct 22:22 | Fail |
| [`rolling-cohort.md`](rolling-cohort.md) | `0128e2b`, 17 Sep 20:54 | same commit | Fail |

## How much the timestamps prove

The last row is the weak one, and most of my early files are like it. The file was written before the test ran, but I committed the file and the result together, so git can't show which came first. You'd be taking my word for it.

From late September I started committing the file first and then running the test. There are 115 of these files in the private repo, and for at least 16 the commit history shows the file going in before the result. The first three rows are examples.

The LLM1 file was changed after it was first committed, which might look bad, so here's what happened. After freezing it I found that the test material was leaking information to the model (details in [case study 5](../case-studies/05-llm-vs-market-price.md)). I fixed that and committed the changes as amendments, all before looking at any results. I think that's fine as long as it's written down. If I'd changed something after seeing the results, that would be a new test.

## What goes in one

- Why I think it might work, and what would make it worth testing.
- The data, the exact rule, and how fills and costs are modelled.
- The numbers it has to hit, all of them, decided in advance.
- What I'll conclude if it fails, so I can't argue my way out of it later.

There's a blank one in [`TEMPLATE.md`](TEMPLATE.md).
