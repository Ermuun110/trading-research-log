# 3. A +18% result that came from row order

A signal showed +5.9% a trade over two months and +18% on a holdout week. Both numbers came from the order rows happened to be stored in. With the real order it's +0.82% and +0.76%.

## The signal

Buy a coin when a second "followable" wallet buys it within ten minutes of the first. To price the entry I needed the state of the coin at the moment of the signal.

## The bug

The archive I was using has a block number, which is called a "slot" in Solana and a timestamp in whole seconds for each trade. It doesn't have the position of the trade inside the block. Lots of trades share a block. At launch a bundle can put a dozen buys into one.

My lookup took "the latest row at or before the signal", sorted by block and timestamp. When several rows tied, the database just returned one of them. In one launch block it booked my entry at the creation price when the block actually ended 3.4 times higher.

So the backtest was buying at a price that was gone before the block finished, ahead of trades it couldn't possibly have been ahead of. Nothing crashed. The numbers looked reasonable. The holdout passed.

## How I found it

I had a second evaluator and ran both on the same trades as a check. They disagreed. I didn't trust either one until I understood why.

## The fix

A pump.fun trade records how many tokens are left in the pool after it. If you know the size of the trade you can work out how many there were before it (add the tokens back for a buy, take them away for a sell). Inside a block, every trade's "before" number is some other trade's "after" number, so you can link them up into a chain. The last trade in the block is the one whose "after" isn't anyone else's "before".

That works for 99.4% of blocks. For the rest I assume the worst case for my strategy. The original script is [`research/g13_exact_intra_slot_order.py`](../research/g13_exact_intra_slot_order.py) and there's a cleaner tested version in [`audit/order.py`](../audit/order.py).

## Result

| | Old lookup | Real order |
|---|---|---|
| July to August | +5.9% a trade | +0.82% (764 trades, day-clustered t of 0.50) |
| Holdout week | +18% (23 trades) | +0.76%, median −1.88% |

I did try to rescue it. With the protocol written down first, I searched 13,680 variations on the first period and tested the top five on the second. None passed. Getting in one block sooner made no difference once the order was right. A small take-profit gave a median of +24% but an average of about zero.

## What I do differently

"The state at block S" now means the last trade in that block, found by chaining. If the data source has a transaction index I use that. Entries fill at the worst price in the block they land in. Any new evaluator gets run against the old one before I believe either. And I've stopped treating a holdout with 23 trades as confirmation of anything.
