# Code from the private repo

Four files, unedited. They only use the Python standard library, because the server they ran on was a small VM without pandas or scikit-learn.

- [`flush_paper.py`](flush_paper.py): paper trader for the "buy after a sharp drop" strategy on Hyperliquid perps. It gets candles over a small websocket client written from scratch (polling 79 coins over REST would have gone over the rate limit). Entries and exits are filled by walking the live order book, with taker fees on both sides. It runs as it is: public API, no keys, no real orders.
- [`kal_paper.py`](kal_paper.py): paper quoter for Kalshi's 15-minute markets. It places a pretend order, works out its place in the queue from the live book, and only counts it as filled if real trades go through at that price. The order never gets cancelled or moved, which is the worst case for a slow trader. Also runs as it is on public data.
- [`fill_model_strategy.py`](fill_model_strategy.py): entry filter, exits and paper fills for the wallet-following strategy on pump.fun. It won't run by itself because it imports other modules I haven't published.
- [`gbm.py`](gbm.py): runs a scikit-learn gradient-boosted model from an exported JSON file with no dependencies. Its output was checked against scikit-learn's on the same inputs and matched exactly. It needs a model file to do anything.

The scripts in [`../research`](../research) need the datasets, which aren't published, apart from `era_metrics.py` which runs on the CSV in [`../data`](../data).
