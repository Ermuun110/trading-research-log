# 7. Why a sub-millisecond copier still lost

In October I worked on two copy-trading bots where the whole bet was speed, one on Solana's pump.fun and one on Robinhood Chain. By the end the Solana bot went from the trader's transaction reaching my server's network card to my own buy being signed in a median 0.29 ms, and the Robinhood bot went from reading a block to sending in 235 microseconds. Neither got the seat that pays.

## Solana

Some pump.fun traders get copied the moment they buy. On paper the first buy behind them was worth +15.5%, the second +6.0%, the third +1.9% and the fourth 0.0%. My first live runs from Frankfurt landed a median 64 ms behind the trader, at seat 6. Moving to Amsterdam, keeping a direct QUIC connection to the leader open and moving the hot path into one Rust thread got 40 probes to a median of 36.9 ms.

## Where the time went

On the leaders I raced on (Jito's BAM client), transactions enter the block through a batch auction every 20 ms, and each round's start is stamped on chain. Calling the trader's round k, my buys mostly landed in round k+2. A millisecond only counts if it gets you into k+1, and that line falls about 19.5 ms after his round closes.

| Piece of the delay | Size |
|---|---|
| My server, network card to signed buy | 0.29 ms median |
| Wire to the BAM node | about 0.8 ms |
| His round closing to his shred reaching me | median 18 to 20 ms |
| Waiting for the next round | a whole round on most sends |

Only the first two rows were mine, and what was left to try on the server was worth about 0.04 to 0.05 ms together. With everything on, 3 of 40 probes made k+1. Bigger tips and fees didn't get me in earlier either.

On Amsterdam-node leaders, the 15 wallets that made k+1 most often made it on 147 of 152 touches, including 30 of 31 where his shred reached me after k+1 had already closed, so they see the result of his round before any shred exists. A pre-confirmation feed might give me that view, but on 488 fresh events the seat it would buy was worth +0.05% a signal, so I didn't buy one.

## Robinhood Chain

Robinhood Chain has one sequencer that takes transactions first come first served, with blocks about 103 ms apart. Here the copy signal passed walk-forward: on 14 windows I hadn't looked at, the first buy in the block after a followed leader's averaged +4.58% after fees at 60 seconds (n 957). Seat 2 was −0.02% and seat 3 −2.58%.

From an AWS box about 1.2 ms from the sequencer, an hour of gas-only probes landed a median 0.71 of the way through the next block. Behind the listed leaders, in blocks where someone else also bought the coin, I was first in 1 of 12. The 21 wallets ahead of me were all reactors, and if transactions arrive evenly through a block (a prediction, since I only measured positions) they see the leader's block 5 to 40 ms before the public feed gets it to me. Another crowd buys inside the leader's own block, which looks like a copy-trading platform or one coordinated group.

## How it was measured

Seats came from the chain's own blocks, after a paper model's seat 2 to 3 turned out to be seat 6. Each change had its pass mark written before the run, and changes on the server were judged against the old version running on the same stream. Anything converted from block position to milliseconds is marked as a prediction.

## What it cost

On Solana, read from the wallet on chain: seven live hours at 0.01 SOL a buy lost 0.04963 SOL, mostly priority fees on buys that failed their price cap, and a Sender tip test lost 0.115 SOL. The five probe runs I have numbers for cost 0.0036 to 0.0186 SOL each, and I haven't summed them. On Robinhood Chain every probe was gas-only, from a wallet funded with 0.0009 ETH.

## Where it stands

The Solana pass mark, a median of 30 ms or less behind him, was never met, so nothing was sized up. On Robinhood Chain the formal seat probe hadn't reached its sample size when I wrote this, and I expect it to fail. In both cases the part of the delay I could work on was the small part.
