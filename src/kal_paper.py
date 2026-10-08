"""PREREG-KAL3 — forward PAPER quoter for Kalshi 15-minute crypto up/down markets. PAPER ONLY.

No account, no API key, no orders: public market data over REST, results in a local sqlite file.
FROZEN 2026-10-05 before the first forward row (update.md 2026-10-05 (16)-(17)).

What it tests: PREREG-KAL2 found that resting orders which SELL the cheap side (<= 5c) in the last minutes of the
SOL / XRP / DOGE markets earn ~+0.8c per contract. That was other makers' fills and a quote replay. This book asks
what OUR order would have got: it posts a paper order, takes its queue position from the live book, and fills it
only from real trade prints. The order is STATIC (never cancelled, never re-priced) - the slow-quoter worst case.

Rule, per market and coin, while 60 s <= time left <= 300 s and one side's ask is <= 5c ("cheap side"):
  selling the cheap side at price p == bidding the favourite at q = 1 - p. Size 100 contracts. One order per arm.
  QUOTE    control: assumed sold at the cheap ask at once (the candle replay; not a fill model).
  JOIN     bid the favourite at the current best favourite bid; queue ahead = size displayed there.
  IMPROVE  bid one tick (0.1c) above the best favourite bid if that is still below the favourite ask; queue ahead 0.
Fill, from prints after the order (+0.3 s): a taker buying the cheap side at favourite price f
  f <  q : filled (our level was walked through);  f == q : consumes the queue ahead first, then us;  f > q : nothing.
  JOIN's queue ahead is also capped by the size displayed at q on every poll.
P&L per filled contract = (1 - q) if the favourite wins, else -q. Maker fee 0 (series fee_type 'quadratic').
Coins: SOL, XRP, DOGE are the test; ETH and BTC are recorded as controls and are NOT in the gate.
Gate, per arm (JOIN, IMPROVE), SOL+XRP+DOGE pooled, read once at >= 300 filled orders AND >= 10 days:
  mean P&L per filled contract > +0.30c, t over 15-minute windows >= 2, >= 60% of days positive.
  Pass = worth a talk about a real account at minimum size. Fail = closed. No rule changes before the read.
Also logged for later (no decisions here): Coinbase spot at every poll, to test a "do not quote near the strike" guard.

PREREG-KAL4 extra arms, added 2026-10-05 (update.md 2026-10-05 (18)). The KAL3 arms above, their orders and their gate
are UNCHANGED; these are separate orders with their own rows (arm name + suffix), same size, same fill rule.
  *_CL3  "calm + late": placed only with 60..180 s left AND the cheap side's ask was <= 15c on every poll of the
         trailing 150 s (>= 140 s of history). In-sample replay: worst day -186 c vs -717 c, +0.55 c/contract. GATED.
  *_L3   "late" only: 60..180 s left. Replay +0.73 c, worst day -70 c, but it MISSED the KAL4 gate (worst-1% window
         improved 24%, bar 30%). OBSERVER arm, not gated: it shows what the calm filter adds.
Gate for JOIN_CL3 / IMPROVE_CL3 (SOL+XRP+DOGE), read once at >= 300 filled orders AND >= 10 days: the three KAL3 bars,
  AND worst day / mean day no worse than the matching KAL3 arm over the same days. No rule changes before the read.
"""
import calendar
import json
import os
import sqlite3
import time
import urllib.request

B = "https://api.elections.kalshi.com/trade-api/v2"
COINS = {"SOL": "KXSOL15M", "XRP": "KXXRP15M", "DOGE": "KXDOGE15M", "ETH": "KXETH15M", "BTC": "KXBTC15M"}
if os.environ.get("KAL_SERIES"):                     # second process (PREREG-KAL6 series), e.g. "COPPER,NATGAS": own db via KAL_DB
    COINS = {c: f"KX{c}15M" for c in os.environ["KAL_SERIES"].split(",")}
SPOT = not os.environ.get("KAL_SERIES")              # Coinbase spot exists only for the crypto set
DB = os.environ.get("KAL_DB") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "kal.db")
SIZE, CHEAP, TICK = 100.0, 0.05, 0.001
T_FROM, T_TO, WATCH = 300, 60, 330
ARMS = ("QUOTE", "JOIN", "IMPROVE")
GUARDS = (("", T_FROM, None), ("_L3", 180, None), ("_CL3", 180, 0.15))    # suffix, max seconds left, calm cap
CALM_S, CALM_MIN = 150, 140


def get(u, timeout=6):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "kal-paper/1 (read-only research)", "Accept": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except Exception:
        return None


def ts(s):
    base = time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
    frac = float("0" + s[19:].rstrip("Z")) if len(s) > 20 and s[19] == "." else 0.0
    return calendar.timegm(base) + frac


def db():
    c = sqlite3.connect(DB, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        ticker TEXT, coin TEXT, arm TEXT, close REAL, placed REAL, left REAL, fav TEXT, q REAL, cheap_ask REAL,
        ahead0 REAL, ahead REAL, filled REAL DEFAULT 0, fill_ts REAL, spot REAL, strike REAL, result TEXT, pnl REAL,
        PRIMARY KEY(ticker, arm))""")
    c.execute("CREATE TABLE IF NOT EXISTS snaps(ts REAL, ticker TEXT, left REAL, yes_bid REAL, yes_ask REAL, bid_sz REAL, ask_sz REAL, spot REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    c.commit()
    return c


def current_market(series, now):
    j = get(f"{B}/markets?series_ticker={series}&status=open&limit=10")
    best = None
    for m in (j or {}).get("markets", []):
        c = ts(m["close_time"])
        if c > now + 5 and (best is None or c < best["close"]):
            best = dict(ticker=m["ticker"], close=c, strike=m.get("floor_strike"))
    return best


def book(ticker):
    j = get(f"{B}/markets/{ticker}/orderbook")
    ob = (j or {}).get("orderbook_fp")
    if ob is None:
        return None
    out = {}
    for side in ("yes", "no"):
        lv = [(float(p), float(s)) for p, s in ob.get(f"{side}_dollars") or [] if float(s) > 0]
        out[side] = dict(lv)
        out[side + "_best"] = max(out[side]) if lv else 0.0
    return out


def spot(coin):
    j = get(f"https://api.exchange.coinbase.com/products/{coin}-USD/ticker", 4)
    try:
        return float(j["price"])
    except Exception:
        return None


def new_prints(st):
    """prints not seen yet for this market, oldest first"""
    out, cur = [], None
    for _ in range(5):
        j = get(f"{B}/markets/trades?ticker={st['ticker']}&limit=1000&min_ts={int(st['last_ts']) - 3}" + (f"&cursor={cur}" if cur else ""))
        tr = (j or {}).get("trades") or []
        for x in tr:
            if x["trade_id"] not in st["seen"]:
                st["seen"].add(x["trade_id"])
                out.append(x)
        cur = (j or {}).get("cursor")
        if not cur or len(tr) < 1000:
            break
    out.sort(key=lambda x: x["created_time"])
    if out:
        st["last_ts"] = max(st["last_ts"], ts(out[-1]["created_time"]))
    return out


def step(con, coin, st, now):
    ob = book(st["ticker"])
    if ob is None:
        return
    now = time.time()                                 # the order exists only after the book it was priced from
    left = st["close"] - now
    sp = spot(coin) if SPOT else None
    yb, nb = ob["yes_best"], ob["no_best"]
    ya = 1 - nb if nb else 1.0
    st["hist"].append((now, ya, 1 - yb if yb else 1.0))
    con.execute("INSERT INTO snaps VALUES(?,?,?,?,?,?,?,?)", (now, st["ticker"], left, yb, ya, ob["yes"].get(yb, 0), ob["no"].get(nb, 0), sp))
    # place paper orders
    if T_TO <= left <= T_FROM and yb and nb:
        cheap = "yes" if 0 < ya <= CHEAP else ("no" if 0 < 1 - yb <= CHEAP else None)
        if cheap:
            fav = "no" if cheap == "yes" else "yes"
            fbid, fask = (nb, 1 - yb) if fav == "no" else (yb, 1 - nb)
            hist = [(t, a if cheap == "yes" else b) for t, a, b in st["hist"] if t >= now - CALM_S]
            for sfx, t_from, calm in GUARDS:
                if left > t_from or (calm is not None and (not hist or now - hist[0][0] < CALM_MIN or max(x for _, x in hist) > calm)):
                    continue
                for base in ARMS:
                    arm = base + sfx
                    if arm in st["orders"]:
                        continue
                    if base == "IMPROVE":
                        q, ahead = round(fbid + TICK, 4), 0.0
                        if q >= fask - 1e-9:
                            continue                  # spread is one tick: cannot improve now, try next poll
                    else:
                        q, ahead = fbid, ob[fav].get(fbid, 0.0)
                    o = dict(arm=arm, placed=now, fav=fav, q=q, ahead=ahead, filled=SIZE if base == "QUOTE" else 0.0)
                    st["orders"][arm] = o
                    con.execute("INSERT OR IGNORE INTO orders(ticker,coin,arm,close,placed,left,fav,q,cheap_ask,ahead0,ahead,filled,fill_ts,spot,strike)"
                                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (st["ticker"], coin, arm, st["close"], now, left, fav, q, round(1 - fbid, 4), ahead, ahead, o["filled"],
                                 now if base == "QUOTE" else None, sp, st["strike"]))
    # queue cap from the live book, then fills from prints
    for o in st["orders"].values():
        if o["arm"].startswith("JOIN") and o["filled"] < SIZE:
            o["ahead"] = min(o["ahead"], ob[o["fav"]].get(o["q"], 0.0))
    for x in new_prints(st):
        t = ts(x["created_time"])
        for o in st["orders"].values():
            if o["arm"].startswith("QUOTE") or o["filled"] >= SIZE or t < o["placed"] + 0.3 or x["taker_side"] == o["fav"]:
                continue
            f = float(x["no_price_dollars"] if o["fav"] == "no" else x["yes_price_dollars"])
            c = float(x["count_fp"])
            got = 0.0
            if f < o["q"] - 1e-9:
                got = SIZE - o["filled"]
            elif abs(f - o["q"]) <= 1e-9:
                o["ahead"] -= c
                if o["ahead"] < 0:
                    got = min(SIZE - o["filled"], -o["ahead"])
                    o["ahead"] = 0.0
            if got > 0:
                first = o["filled"] == 0
                o["filled"] += got
                con.execute("UPDATE orders SET filled=?, ahead=?, fill_ts=COALESCE(fill_ts,?) WHERE ticker=? AND arm=?",
                            (o["filled"], o["ahead"], t if first else None, st["ticker"], o["arm"]))
    for o in st["orders"].values():
        con.execute("UPDATE orders SET ahead=? WHERE ticker=? AND arm=? AND filled<?", (o["ahead"], st["ticker"], o["arm"], SIZE))
    con.commit()


def settle(con):
    rows = con.execute("SELECT DISTINCT ticker FROM orders WHERE result IS NULL AND close < ?", (time.time() - 20,)).fetchall()
    for (tk,) in rows:
        m = (get(f"{B}/markets/{tk}") or {}).get("market") or {}
        res = m.get("result")
        if res in ("yes", "no"):
            con.execute("UPDATE orders SET result=?, pnl=CASE WHEN fav=? THEN 1-q ELSE -q END WHERE ticker=?", (res, res, tk))
    con.commit()


def main():
    con = db()
    con.execute("INSERT OR IGNORE INTO meta VALUES('started', ?)", (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),))
    con.commit()
    print("kal-paper: PAPER ONLY, no keys, no orders. db", DB, flush=True)
    state, last_settle = {}, 0.0
    while True:
        now = time.time()
        nxt = (int(now) // 900 + 1) * 900            # every market closes on the quarter hour
        left = nxt - now
        if left > WATCH:
            if now - last_settle > 30:
                settle(con)
                last_settle = now
                con.execute("DELETE FROM snaps WHERE ts < ?", (now - 45 * 86400,))
                con.commit()
            time.sleep(min(20, left - WATCH))
            continue
        t0 = time.time()
        for coin, series in COINS.items():
            st = state.get(coin)
            if st is None or st["close"] <= now:
                m = current_market(series, now)
                if not m or m["close"] - now > 900:
                    continue
                st = state[coin] = dict(m, orders={}, seen=set(), last_ts=now, hist=[])
            if 0 < st["close"] - time.time() <= WATCH:
                try:
                    step(con, coin, st, time.time())
                except Exception as e:                                   # one bad response must not stop the book
                    print("step error", coin, repr(e)[:200], flush=True)
        time.sleep(max(0.2, 1.5 - (time.time() - t0)))


if __name__ == "__main__":
    main()
