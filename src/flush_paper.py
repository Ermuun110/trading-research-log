"""Flush-reversion PAPER trader on Hyperliquid perps. Stdlib only, no keys, no orders.

Rule (pre-registered 2026-09-19 from research/scratch/2026-09-19-momentum/m5-m7):
at the close of 1m candle t, if close/open-1 <= -Y and quote volume >= K x the median
of the previous 60 minutes, go LONG; exit H minutes later. One position per coin per arm.

Honest fill: entry walks the live ASK side of the L2 book for NOTIONAL USD, exit walks
the BIDS; taker fee charged both sides. The candle open of t+1 is also recorded so the
live fill can be compared to what the backtest assumed.

Candles arrive over the HL websocket (a small stdlib client below): polling 79 coins by
REST each minute would exceed HL's 1200 weight/min limit. REST is the fallback when the
socket has been silent for 90s.

Every trade stores `breadth` = coins that flushed (<= -1% on >= 5x volume) in the same
minute. The crash cap is judged from that column later, not guessed now.
"""
import base64, json, os, signal, socket, sqlite3, ssl, statistics, struct, sys, threading, time, urllib.request

API = "https://api.hyperliquid.xyz/info"
DB = os.environ.get("FLUSH_DB", os.path.expanduser("~/Bot/flush.db"))
NOTIONAL = 1000.0
FEE = 0.00045                      # HL base-tier taker, per side
MAJORS = ("BTC ETH SOL XRP SUI ADA AVAX LINK DOT LTC BNB NEAR APT ARB OP INJ SEI TIA "
          "ORDI WLD ENA JUP ONDO HYPE TAO").split()
MEMES = ("DOGE kPEPE WIF kBONK kFLOKI kSHIB BOME POPCAT TRUMP FARTCOIN PNUT GOAT MOODENG "
         "kNEIRO TURBO PEOPLE BRETT SPX VIRTUAL PENGU").split()
# every HL perp > $2M/day that also has Binance history (m8: 62 coins, 34 never in m5-m7)
LIQUID = ("BTC ETH ZEC HYPE SOL NEAR XRP UNI LIT XMR ARB ENA PUMP VVV TAO ONDO STRK XPL WLD kPEPE SUI "
          "LTC BNB ADA AAVE USELESS FARTCOIN AVAX INJ AERO CRV DOGE LINK ETHFI MON JUP AR ASTER APT XLM "
          "TRUMP PENDLE CHIP BCH ZEN FIL MORPHO ZRO kBONK DASH PENGU FET OP SAGA EIGEN JTO MEGA ICP POL "
          "GRAM LDO WIF").split()
# arm: (group, trigger kind, dump Y, volume multiple K, hold minutes)
#   r1  = 1m return <= -Y, 1m vol >= K x median(prev 60m)
#   r3  = 3m return <= -Y, 3m vol >= K x 3 x median(60m ending 5m ago)   (r5 likewise over 5m)
#   rel = 1m return minus BTC's 1m return <= -Y, 1m vol >= K x median(prev 60m)
ARMS = {
    "M2_60":  (MAJORS, "r1", 0.02, 10, 60),     # the original headline cell
    "M3_240": (MAJORS, "r1", 0.03, 10, 240),
    "M1_60":  (MAJORS, "r1", 0.01, 10, 60),
    "K2_60":  (MEMES,  "r1", 0.02, 10, 60),
    "L2_60":  (LIQUID, "r1", 0.02, 10, 60),     # 09-19 frequency upgrade (m8)
    "L2_120": (LIQUID, "r1", 0.02, 10, 120),
    "L15_60": (LIQUID, "r1", 0.015, 10, 60),
    # 09-19 lever study (m9), the only levers that held on the untouched Sep 1-18 slice
    "C5_60":  (LIQUID, "r5", 0.05, 5, 60),      # P1+2 +1.05% / P3 +0.95%, ~1.4/day
    "D3_60":  (LIQUID, "r1", 0.03, 10, 60),     # P1+2 +1.32% / P3 +0.44%, ~2/day
    "R2_60":  (LIQUID, "rel", 0.02, 10, 60),    # P1+2 +0.59% / P3 +0.41%, ~3.6/day
    "C3_60":  (LIQUID, "r3", 0.02, 5, 60),      # P1+2 +0.23% / P3 +0.23%, ~11/day
}
# HL perps $0.3-2M/day with Binance history (m11): thinner books, so smaller paper size
SMALL = ("ATOM DYDX STX TRX kSHIB SEI DOT KAS TIA MINA PYTH SUSHI SUPER CAKE ETC W HBAR REZ ZK RENDER "
         "GOAT GRASS SAND ALGO VIRTUAL USUAL BIO SPX S KAITO NIL PAXG SYRUP WLFI SKY AVNT 0G HEMI MET CC "
         "FOGO AXS SKR AZTEC").split()
ARMS.update({
    # 09-19 slow-flush study (m10): chosen on Sep25-Feb26 ONLY, confirmed on Mar-Aug and Sep 1-18
    "F15_60":  (LIQUID, "r15", 0.05, 3, 60),    # +1.34 / +1.04 / +1.19%, t 3.7 / 1.3 / 3.3, ~3.5/day
    "F15_240": (LIQUID, "r15", 0.05, 3, 240),   # +0.69 / +0.96 / +1.85%
    "H60_240": (LIQUID, "r60", 0.08, 2, 240),   # +0.69 / +2.61 / +2.11%, ~1.5/day
    "F5_60":   (LIQUID, "r5", 0.04, 5, 60),     # +0.94 / +1.28 / +0.43%, ~3/day
    "S15_60":  (SMALL, "r15", 0.05, 3, 60, 300.0),  # m11 small coins @0.40% RT: +0.70 / +0.72 / +0.34%
})
COINS = list(dict.fromkeys(MAJORS + MEMES + LIQUID + SMALL))
WS_LAST = [0.0]
HIST = 1500                        # r60 needs a 1440m volume median ending 60m ago
RUN = True


def info(body, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(API, json.dumps(body).encode(), {"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=15))
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(2 + 3 * k)


def candles(coin, minutes):
    now = int(time.time() * 1000)
    rows = info({"type": "candleSnapshot",
                 "req": {"coin": coin, "interval": "1m", "startTime": now - minutes * 60000, "endTime": now}})
    return {int(r["t"]): (float(r["o"]), float(r["c"]), float(r["v"]) * float(r["c"])) for r in rows}


def ws_frame(sock, payload, op=1):
    data = payload.encode() if isinstance(payload, str) else payload
    mask = os.urandom(4)
    n = len(data)
    head = bytes([0x80 | op]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n)
                                 if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n))
    sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def ws_recv(f):
    """One complete message (opcode, bytes). Server frames are unmasked."""
    buf, op0 = b"", None
    while True:
        b0, b1 = f.read(2)
        op, n = b0 & 0x0F, b1 & 0x7F
        if n == 126:
            n = struct.unpack(">H", f.read(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", f.read(8))[0]
        data = f.read(n)
        if op >= 8:                                  # control frame: ping/pong/close
            return op, data
        op0 = op0 if op == 0 else op
        buf += data
        if b0 & 0x80:
            return op0, buf


def ws_loop(hist):
    """Keep hist[coin][t] = (o, c, quote_vol) current from the candle stream. Reconnects forever."""
    while RUN:
        try:
            raw = socket.create_connection(("api.hyperliquid.xyz", 443), timeout=60)
            sock = ssl.create_default_context().wrap_socket(raw, server_hostname="api.hyperliquid.xyz")
            key = base64.b64encode(os.urandom(16)).decode()
            sock.sendall((f"GET /ws HTTP/1.1\r\nHost: api.hyperliquid.xyz\r\nUpgrade: websocket\r\n"
                          f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
            f = sock.makefile("rb")
            if b" 101 " not in f.readline():
                raise RuntimeError("ws handshake refused")
            while f.readline() not in (b"\r\n", b""):
                pass
            for coin in COINS:
                ws_frame(sock, json.dumps({"method": "subscribe",
                                           "subscription": {"type": "candle", "coin": coin, "interval": "1m"}}))
            print(f"ws up, {len(COINS)} candle subscriptions", flush=True)
            last_ping = time.time()
            while RUN:
                if time.time() - last_ping > 30:
                    ws_frame(sock, json.dumps({"method": "ping"})); last_ping = time.time()
                op, data = ws_recv(f)
                if op == 9:
                    ws_frame(sock, data, 10); continue
                if op == 8:
                    raise RuntimeError("ws closed by server")
                if op != 1:
                    continue
                msg = json.loads(data)
                if msg.get("channel") == "candle":
                    d = msg["data"]
                    if d["s"] in hist:
                        hist[d["s"]][int(d["t"])] = (float(d["o"]), float(d["c"]), float(d["v"]) * float(d["c"]))
                        WS_LAST[0] = time.time()
        except Exception as e:
            print(f"ws down: {e}; reconnect in 5s", flush=True)
            time.sleep(5)


def walk(coin, side, notional=NOTIONAL):
    """Average fill price for `notional` USD against the book. side 0 = bids (sell), 1 = asks (buy)."""
    b = info({"type": "l2Book", "coin": coin})
    lv = b["levels"][side]
    mid = (float(b["levels"][0][0]["px"]) + float(b["levels"][1][0]["px"])) / 2
    left, cost, qty = notional, 0.0, 0.0
    for l in lv:
        px, sz = float(l["px"]), float(l["sz"])
        take = min(left, px * sz)
        cost += take; qty += take / px; left -= take
        if left <= 1e-9:
            break
    return cost / qty, mid, left > 1e-6


def db():
    c = sqlite3.connect(DB)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY, arm TEXT, coin TEXT, trig_min INTEGER, dump REAL, volx REAL,
        breadth INTEGER, entry_ts REAL, entry_px REAL, entry_mid REAL, entry_thin INTEGER,
        next_open REAL, exit_due REAL, exit_ts REAL, exit_px REAL, exit_mid REAL,
        exit_close REAL, ret_net REAL, ret_open REAL, status TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS wscheck (ts REAL, coin TEXT, minute INTEGER,
        ws_o REAL, ws_c REAL, ws_qv REAL, rest_o REAL, rest_c REAL, rest_qv REAL)""")
    c.execute("CREATE TABLE IF NOT EXISTS heartbeat (ts REAL, minute INTEGER, coins_ok INTEGER, flushes INTEGER)")
    return c


def main():
    signal.signal(signal.SIGTERM, lambda *a: globals().__setitem__("RUN", False))
    con = db()
    hist = {}
    for coin in COINS:                                  # bootstrap history, paced
        try:
            hist[coin] = candles(coin, HIST + 5)
        except Exception as e:
            print(f"bootstrap {coin}: {e}", flush=True)
            hist[coin] = {}
        time.sleep(2.5)                                 # ~45 weight per 1500-candle pull
    threading.Thread(target=ws_loop, args=(hist,), daemon=True).start()
    print(f"flush paper up: {len(COINS)} coins, arms={list(ARMS)}, db={DB}", flush=True)
    last_min = int(time.time() // 60) * 60000 - 60000
    while RUN:
        now = time.time()
        closed = int(now // 60) * 60000 - 60000        # most recent fully closed minute
        if closed > last_min and now % 60 >= 2.5:
            scan(con, hist, closed)
            last_min = closed
        exits(con)
        time.sleep(2)


def scan(con, hist, t):
    ok, sig = 0, {}
    rest = time.time() - WS_LAST[0] > 90             # socket silent: fall back to REST polling
    for coin in COINS:
        if rest:
            try:
                hist[coin].update(candles(coin, 3))
            except Exception as e:
                print(f"candles {coin}: {e}", flush=True)
                continue
        ok += 1
        h = hist[coin]
        for k in [k for k in list(h) if k < t - (HIST + 5) * 60000]:
            del h[k]
        if t not in h:
            continue
        o, c, qv = h[t]
        vol = lambda k: h[k][2] if k in h else 0.0
        f = {}
        # window n minutes, volume baseline = median of `base` minutes ending `lag` minutes before t
        # (matches the backtest's rolling(base).median().shift(lag)); a zero baseline skips the feature
        for n, base, lag in ((1, 60, 1), (3, 60, 5), (5, 60, 5), (15, 240, 15), (60, 1440, 60)):
            med = statistics.median(vol(k) for k in range(t - (base + lag - 1) * 60000, t - (lag - 1) * 60000, 60000))
            if med <= 0:
                continue
            ks = [k for k in range(t - (n - 1) * 60000, t + 1, 60000) if k in h]
            f[f"r{n}"] = (c / h[ks[0]][0] - 1, sum(vol(k) for k in ks) / (n * med))
        if f:
            sig[coin] = f
    breadth = sum(1 for f in sig.values() if "r1" in f and f["r1"][0] <= -0.01 and f["r1"][1] >= 5)
    btc = sig.get("BTC", {}).get("r1", (0.0, 0))[0]
    for f in sig.values():
        if "r1" in f:
            f["rel"] = (f["r1"][0] - btc, f["r1"][1])
    con.execute("INSERT INTO heartbeat VALUES (?,?,?,?)", (time.time(), t, ok, breadth))
    wscheck(con, hist, t)
    for arm, (grp, kind, y, k, H, *size) in ARMS.items():
        for coin in grp:
            if kind not in sig.get(coin, {}):
                continue
            d, x = sig[coin][kind]
            if d > -y or x < k:
                continue
            if con.execute("SELECT 1 FROM trades WHERE arm=? AND coin=? AND status='open'", (arm, coin)).fetchone():
                continue
            try:
                px, mid, thin = walk(coin, 1, *size)
            except Exception as e:
                print(f"entry book {coin}: {e}", flush=True)
                continue
            ts = time.time()
            con.execute("""INSERT INTO trades (arm, coin, trig_min, dump, volx, breadth, entry_ts, entry_px,
                           entry_mid, entry_thin, exit_due, status) VALUES (?,?,?,?,?,?,?,?,?,?,?, 'open')""",
                        (arm, coin, t, d, x, breadth, ts, px, mid, int(thin), ts + H * 60))
            print(f"ENTER {arm} {coin} {kind}={d*100:+.2f}% vol={x:.1f}x breadth={breadth} "
                  f"px={px:.6g} mid={mid:.6g} lag={ts - t/1000 - 60:.1f}s", flush=True)
    con.commit()


def wscheck(con, hist, t):
    """Data-quality audit: the socket's view of a candle 3 minutes old vs REST's finished candle,
    one rotating coin per scan. A mismatch means triggers are computed on incomplete candles."""
    m = t - 3 * 60000
    coin = COINS[(t // 60000) % len(COINS)]
    if m not in hist.get(coin, {}):
        return
    try:
        rest = candles(coin, 6).get(m)
    except Exception:
        return
    if rest:
        con.execute("INSERT INTO wscheck VALUES (?,?,?,?,?,?,?,?,?)", (time.time(), coin, m, *hist[coin][m], *rest))


def exits(con):
    now = time.time()
    for tid, coin, epx, tmin, eh, arm in con.execute(
            "SELECT id, coin, entry_px, trig_min, exit_due, arm FROM trades WHERE status='open' AND exit_due <= ?",
            (now,)).fetchall():
        try:
            px, mid, thin = walk(coin, 0, *ARMS.get(arm, (0,) * 5)[5:])
        except Exception as e:
            print(f"exit book {coin}: {e}", flush=True)
            continue
        ret = px * (1 - FEE) / (epx * (1 + FEE)) - 1
        con.execute("UPDATE trades SET exit_ts=?, exit_px=?, exit_mid=?, ret_net=?, status='closed' WHERE id=?",
                    (now, px, mid, ret, tid))
        print(f"EXIT {coin} ret={ret*100:+.2f}% thin={thin}", flush=True)
    # backtest-parity fields: next-minute open at entry, and the candle close at the due minute
    for tid, coin, tmin, due in con.execute(
            "SELECT id, coin, trig_min, exit_due FROM trades WHERE status='closed' AND ret_open IS NULL "
            "AND exit_ts < ?", (now - 120,)).fetchall():
        try:
            nxt = info({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1m",
                        "startTime": tmin + 60000, "endTime": tmin + 120000}})
            end = info({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1m",
                        "startTime": int(due * 1000) - 120000, "endTime": int(due * 1000)}})
            if not nxt or not end:
                continue
            no, ec = float(nxt[0]["o"]), float(end[-1]["c"])
            con.execute("UPDATE trades SET next_open=?, exit_close=?, ret_open=? WHERE id=?",
                        (no, ec, ec / no - 1 - 2 * FEE, tid))
        except Exception as e:
            print(f"parity {coin}: {e}", flush=True)
    con.commit()


if __name__ == "__main__":
    sys.exit(main())
