"""Entry filter + exit management — the backtested rules, PAPER fills, on live
data (PumpPortal signal + Helius bonding-curve reserves).

Entry (called ENTRY_DELAY_S after a cohort wallet's buy):
  reject if graduated / no reserves / already held (this variant) / slots full
  reject if liquidity (real SOL in curve) < LIQ_MIN_SOL_FLOOR
  reject if net SOL inflow over the wait window < MIN_NET_INFLOW_SOL
    (LIVE PROXY for the backtested 'buys > 2x sells': net buying demand, cheap
     to compute from two reserve reads; re-validate vs counts once live data
     accumulates).
  else paper-buy POSITION_USD at the exact bonding-curve fill.

Exit (each poll): NO STOP. take_profit at TP_MULT, else graduated/timeout/
delisted. Fills on current reserves (real slippage for our bag).
"""
import time

from . import config, curve, executor, helius, jup, store, wxc

# Wallets auto-demoted from live copied outcomes (refreshed by main loop via
# refresh_scorecard). Unioned with the static config.BLACKLIST_WALLETS.
DYNAMIC_BLACKLIST = set()


def refresh_scorecard(c):
    """Recompute the auto-demote set from our closed trades. Returns newly-added
    wallets (for logging). Cheap GROUP BY; called on a timer by the main loop."""
    global DYNAMIC_BLACKLIST
    fresh = store.demoted_wallets(
        c, config.SCORECARD_MIN_N, config.SCORECARD_AVG_LE, config.SCORECARD_SUM_LE)
    new = fresh - DYNAMIC_BLACKLIST - config.BLACKLIST_WALLETS
    DYNAMIC_BLACKLIST = fresh
    return new


def _model_gate(c, mint, variant, st, signal_ts, conf, bonding_curve_key):
    """wxc entry gate: score the coin on the four features the model was trained
    on and accept only its top quartile. Returns (verdict, score) — verdict is
    None when the coin PASSES, otherwise the skip reason.

    FAILS CLOSED. The rule was measured with all four features present, so a
    missing model file, a coin whose birth time we cannot establish, or a buy
    with no confluence context takes NO position rather than a guessed one.

    Feature timing matches training (p6.py) exactly:
      log_lam  reserves at our entry, i.e. trigger buy + delay  (LAMPORTS)
      log_age  coin age at the TRIGGER BUY, not at our entry
      n_conf / secs_since_first  measured at the trigger buy, from cohort buys
                                 strictly before it
    """
    if conf is None:
        store.log(c, mint, "skip", f"{variant}:no_conf_ctx")
        return "no_conf_ctx", None
    born = helius.coin_created_ts(mint, bonding_curve_key)
    if born is None:
        store.log(c, mint, "skip", f"{variant}:no_age")
        return "no_age", None
    feats = wxc.features(st["real_sol"], signal_ts - born,
                         conf["n_conf"], conf["secs_since_first"])
    ok, score = wxc.passes(feats)
    if not ok:
        sc = "none" if score is None else f"{score:+.5f}"
        store.log(c, mint, "skip",
                  f"{variant}:wxc_gate score={sc} age{int(signal_ts - born)}s "
                  f"conf{conf['n_conf']}")
        return "wxc_gate", score
    return None, score


def evaluate_entry(c, mint, signal_wallet, signal_ts, sol_usd, variant, delay,
                   bonding_curve_key, real_sol_signal, conf=None):
    # NOFILTER books replay a rule that had NO wallet demotion, so the live
    # scorecard must not prune their cohort — that would make the forward number
    # incomparable to the one it is testing. Static blacklist still applies.
    demoted = (signal_wallet in DYNAMIC_BLACKLIST
               and variant not in config.NOFILTER_VARIANTS)
    if signal_wallet in config.BLACKLIST_WALLETS or demoted:
        src = "seed" if signal_wallet in config.BLACKLIST_WALLETS else "scorecard"
        store.log(c, mint, "skip", f"{variant}:blacklist({src}) {signal_wallet[:6]}")
        return "blacklisted"
    if store.has_position(c, mint, variant):
        return "already_positioned"
    if store.n_open(c, variant) >= config.MAX_CONCURRENT:
        store.log(c, mint, "skip", f"{variant}:slots_full")
        return "slots_full"
    st = helius.curve_state(bonding_curve_key)
    if st is None:
        store.log(c, mint, "skip", f"{variant}:no_reserves")
        return "no_reserves"
    if st["complete"]:
        store.log(c, mint, "skip", f"{variant}:graduated")
        return "graduated"
    # MIGRATION RACE. `complete` is not set atomically with the reserve drain, so
    # there is a window where the curve reads complete=0 with its reserves already
    # emptied into the AMM. Filling there books an entry price off a near-zero
    # denominator and invents a return with no trade behind it: id937 read
    # v_sol=0.012 SOL (the whole curve) and booked +14,749.9% = $6,637, while
    # pump.fun's own program refused the real buy with Custom 6063. 19 wxcc rows
    # did this and carry $11,237 of the book's $14,261 -- 79% of paper's P&L from
    # trades that were never executable.
    #
    # The floor is a PHYSICAL INVARIANT, not a tuned parameter: a pump.fun curve
    # opens at 30 SOL of virtual_sol_reserves and that number only ever rises, so
    # anything below it is not a live curve we could have traded. This is the
    # NOFILTER books' one exception, and it has to be -- it rejects impossible
    # fills, not unattractive ones, so the copy rule being tested is untouched.
    if st["v_sol"] < config.MIN_CURVE_V_SOL_LAMPORTS:
        store.log(c, mint, "skip",
                  f"{variant}:dead_curve v_sol={st['v_sol'] / 1e9:.4f} SOL")
        return "dead_curve"
    net_inflow = st["real_sol"] - real_sol_signal          # SOL bought in window
    if variant not in config.NOFILTER_VARIANTS:
        # d60b keeps its backtested secondary filter. NOFILTER books (v3f) copy
        # the wallet and nothing else — that is exactly the rule that was
        # measured, and adding a gate here would make the forward book untestable
        # against the number it is supposed to confirm.
        liq_floor = config.LIQ_MIN_SOL or config.LIQ_MIN_SOL_FLOOR
        if st["real_sol"] < liq_floor:
            store.log(c, mint, "skip", f"{variant}:liq_low {st['real_sol']:.1f}")
            return "liq_low"
        if net_inflow < config.MIN_NET_INFLOW_SOL:
            store.log(c, mint, "skip",
                      f"{variant}:weak_inflow {net_inflow:+.2f}SOL")
            return "weak_inflow"
    # per-book entry-liquidity floor. Applied to NOFILTER books too: where a book
    # has one it is that arm's reason to exist, and it is checked BEFORE the model
    # so a thin coin is never scored or entered.
    liq_min = config.VARIANT_LIQ_MIN_SOL.get(variant)
    if liq_min is not None and st["real_sol"] < liq_min:
        store.log(c, mint, "skip", f"{variant}:liq_floor {st['real_sol']:.1f}<{liq_min:.0f}")
        return "liq_floor"
    # per-book entry-liquidity BAND. Liquidity is NOT monotone: on the panel a
    # floor keeps improving up to ~25 SOL and then COLLAPSES (>=45 SOL is
    # +0.77%/tr vs +11.45% at 25-45), because above the band the curve is too
    # full for the remaining run to pay. A band, not a floor, is what fits.
    band = config.VARIANT_LIQ_BAND_SOL.get(variant)
    if band is not None:
        lo, hi = band
        if not (lo <= st["real_sol"] <= hi):
            store.log(c, mint, "skip",
                      f"{variant}:liq_band {st['real_sol']:.1f} outside "
                      f"{lo:.0f}-{hi:.0f}")
            return "liq_band"
    # per-book INFLOW VELOCITY gate (wxcv). How fast SOL entered the curve
    # between the first cohort sighting and this confirming buy, as a 60s rate.
    # Both levels are already in hand — the feed reports the curve level on every
    # cohort buy message, and we just read the trigger level above — so this
    # costs no extra call and adds no latency. The rule is NOT "find graduators":
    # the panel says predicting graduation is easy and unprofitable, because
    # every predictor of it means "already near the top". This band keeps the
    # payoff large (E[r|graduated] +240.8% vs +110.2% for the book) instead of
    # chasing the probability.
    rate_min = config.VARIANT_MIN_INFLOW_RATE.get(variant)
    if rate_min is not None:
        lam0 = (conf or {}).get("lam_at_first")
        secs = (conf or {}).get("secs_since_first") or 0.0
        if lam0 is None or secs <= 0:
            # No first-sighting level means the feature cannot be computed. Fail
            # CLOSED: entering without the gate would be a different book than
            # the one being tested.
            store.log(c, mint, "skip", f"{variant}:no_inflow_data")
            return "no_inflow_data"
        rate = (st["real_sol"] - lam0) * 60.0 / secs
        if rate < rate_min:
            store.log(c, mint, "skip",
                      f"{variant}:slow_inflow {rate:.1f}<{rate_min:.1f} SOL/60s "
                      f"({st['real_sol']:.1f}-{lam0:.1f} over {secs:.0f}s)")
            return "slow_inflow"
    score = None
    if variant in config.MODEL_VARIANTS:
        verdict, score = _model_gate(c, mint, variant, st, signal_ts, conf,
                                     bonding_curve_key)
        if verdict:
            return verdict
    # PASS -> paper buy at the curve state our order would ACTUALLY land on.
    # Deciding and filling are not the same instant: a real send has to be built,
    # signed, submitted and included. Filling at the reserves we made the
    # decision on hands the paper book a price no order could have taken, so we
    # re-read the curve after the send window and fill THERE. Costs one RPC call
    # on a path that already makes several, and only on candidates that passed.
    # REAL LEG FIRST, in the background. Every gate has passed, so the decision is
    # final; everything below this line is paper pricing itself, and the send has
    # no reason to wait for it. Measured chain-to-chain, waiting cost ~1.3s of a
    # 2.8-3.2s entry -- the sleep just below plus an RPC read -- and the decay
    # table separates <=2s (+16.43%/tr) from 2-5s (+2.32%). It is a THREAD, not a
    # reordering, so the law still holds: paper never reads, waits on, or branches
    # on this handle, and the real leg cannot change what the book records.
    exec_box = None
    try:
        exec_box = executor.start_buy(c, variant, mint, sol_usd)
    except Exception as e:                   # never let the real leg break paper
        store.log(c, mint, "exec_buy_fail", f"{variant} start {e}")
    if config.ENTRY_LATENCY_S > 0:
        time.sleep(config.ENTRY_LATENCY_S)
        st2 = helius.curve_state(bonding_curve_key)
        if st2 is None or st2.get("complete"):
            store.log(c, mint, "skip", f"{variant}:gone_in_flight")
            # The send may already have landed. A real bag with no paper position
            # is invisible to the exit loop, so flatten it rather than hold it.
            try:
                executor.abandon_buy(c, exec_box, variant, mint, "gone_in_flight")
            except Exception as e:
                store.log(c, mint, "exec_orphan_stuck", f"{variant} {mint} {e}")
            return "gone_in_flight"
        st = st2
    pos_usd = config.VARIANT_POSITION_USD.get(variant, config.POSITION_USD)
    size_sol = pos_usd / sol_usd
    size_lam = size_sol * 1e9
    tokens = curve.buy_fill(st["v_sol"], st["v_tok"], size_lam)
    pid = store.open_position(c, {
        "variant": variant, "mint": mint, "symbol": None,
        "signal_wallet": signal_wallet, "signal_ts": signal_ts,
        "entry_ts": int(time.time()), "entry_v_sol": st["v_sol"],
        "entry_v_tok": st["v_tok"], "entry_liq_sol": st["real_sol"],
        "bonding_curve_key": bonding_curve_key,
        "net_inflow": net_inflow, "size_sol": size_sol, "tokens": tokens})
    extra = "" if score is None else f" wxc{score:+.5f} conf{conf['n_conf']}"
    store.log(c, mint, "enter",
              f"{variant} id{pid} liq{st['real_sol']:.1f} inflow{net_inflow:+.2f}"
              + extra)
    print(f"  ENTER[{variant}] {mint[:8]} liq {st['real_sol']:.1f} SOL "
          f"inflow {net_inflow:+.2f}{extra} (paper ${pos_usd:.0f})")
    # The real leg was started BEFORE the paper sleep; collect it now that the
    # position exists and has an id to file it under. Recording happens here, on
    # this thread, because store.connect() is not multi-thread safe.
    try:
        executor.finish_buy(c, exec_box, pid, variant, mint)
    except Exception as e:                   # never let the real leg break paper
        store.log(c, mint, "exec_buy_fail", f"{variant} id{pid} unhandled {e}")
    return "entered"


def _tx_cost_lam():
    """Lamports a real round trip burns beyond the protocol fee.

    Two landed transactions (entry + exit), each paying priority + base, plus
    the expected cost of the attempts that miss and land nothing. Charged in
    lamports so it does not silently vanish as position size grows.
    """
    per_attempt = config.PRIORITY_FEE_LAMPORTS + config.BASE_TX_FEE_LAMPORTS
    attempts = 2.0 / max(1e-9, 1.0 - config.FAILED_TX_RATE)
    return per_attempt * attempts


def _finalize(c, pos, reason, v_sol, v_tok, sol_usd, sol_out_lam=None):
    """Close a position at an honest fill.

    `sol_out_lam` overrides the curve maths with proceeds that were quoted
    somewhere else — used for a graduated bag, which cannot be sold against the
    zeroed curve and is only worth what a router will really pay.
    """
    fee = config.PUMP_FEE_PER_SIDE
    size_lam = pos["size_sol"] * 1e9
    if sol_out_lam is not None:             # router-quoted exit (already net of
        sol_out = sol_out_lam               # its own route impact/slippage)
        pnl_pct = (sol_out / size_lam) * (1 - fee) - 1.0
    elif v_sol is None:                     # account gone / no route = total loss
        pnl_pct = -1.0
    else:
        sol_out = curve.sell_fill(v_sol, v_tok, pos["tokens"])
        pnl_pct = (sol_out / size_lam) * (1 - fee) * (1 - fee) - 1.0
    if pnl_pct > -1.0:                      # a total loss already lost the fees
        pnl_pct -= _tx_cost_lam() / size_lam
    pnl_usd = pos["size_sol"] * sol_usd * pnl_pct
    store.close_position(c, pos["id"], reason, v_sol, v_tok, pnl_pct, pnl_usd)
    print(f"  EXIT[{pos['variant']}/{reason}] {pos['mint'][:8]} "
          f"{pnl_pct*100:+.1f}% (${pnl_usd:+.2f})")
    # Close the real leg too. Attempted for EVERY exit reason including a rug:
    # if there is no route the executor says so and we learn that the bag was
    # genuinely unsellable, which is exactly the fact paper has to get right.
    try:
        executor.sell(c, pos["id"], pos["variant"], pos["mint"])
    except Exception as e:
        store.log(c, pos["mint"], "exec_sell_fail",
                  f"{pos['variant']} id{pos['id']} unhandled {e}")


# pump.fun ZEROES the bonding-curve reserves at graduation (v_sol=v_tok=0,
# complete=True). Pricing the exit against those zeros fakes a -100% on what is
# actually the BEST outcome (the coin reached ~$69k mcap and migrated). So we
# price a graduation at the last reserves seen while the curve was still live
# (≈ the migration price). Fallback = pump.fun's deterministic graduation
# snapshot (~793.1M tokens sold / ~85 SOL raised -> virtual v_sol≈115.0 SOL,
# v_tok≈279.9M @ 6 decimals) for coins that graduate before we poll them.
_GRAD_V_SOL = 115.005e9
_GRAD_V_TOK = 279.9e6 * 1e6
_last_reserves = {}                      # pos_id -> (v_sol, v_tok) pre-graduation
_grad_tries = {}                         # pos_id -> post-migration quote attempts


def _deadline_passed(pos, now):
    """True once this position has reached its fixed-hold deadline. The clock
    starts at the SIGNAL for books whose backtest measured the hold from the
    triggering buy (wxc/wxcr: entry at trigger+60, exit at trigger+900), and at
    our entry for everything else."""
    timeout_s = config.VARIANT_TIMEOUT_S.get(pos["variant"], config.TIMEOUT_S)
    base = (pos["signal_ts"]
            if pos["variant"] in config.VARIANT_TIMEOUT_FROM_SIGNAL
            else pos["entry_ts"])
    return now - base >= timeout_s


def manage(c, sol_usd):
    """Poll each open position; no-stop / TP+200% / graduated / timeout / delist."""
    now = int(time.time())
    for pos in store.open_positions(c):
        pid = pos["id"]
        st = helius.curve_state(pos["bonding_curve_key"])
        if st is None:                       # account gone -> rug (can't sell)
            if _deadline_passed(pos, now):
                _last_reserves.pop(pid, None)
                _finalize(c, pos, "delisted", None, None, sol_usd)
            continue
        if st["complete"]:                   # graduated -> the curve is LOCKED
            # The reserves are zeroed and nothing can be sold against them. The
            # last pre-migration price is a MARK, not a fill: we held through
            # that poll and would only "sell" there with hindsight. Ask a router
            # what the bag is really worth, at our exact size, right now.
            lam, status = jup.sell_quote(pos["mint"], pos["tokens"])
            tries = _grad_tries.get(pid, 0) + 1
            _grad_tries[pid] = tries
            if status == "api_down" or (status == "no_route"
                                        and tries < config.GRAD_QUOTE_RETRIES):
                # Migration has a real gap before the pool is routable. Keep the
                # position OPEN and ask again next poll rather than inventing a
                # price in either direction.
                store.log(c, pos["mint"], "grad_wait",
                          f"{pos['variant']} {status} try{tries}")
                continue
            _last_reserves.pop(pid, None)
            _grad_tries.pop(pid, None)
            held = int(time.time()) - pos["entry_ts"]
            if status == "no_route":         # never became sellable = stuck bag
                store.log(c, pos["mint"], "grad_noroute",
                          f"{pos['variant']} after {tries} tries, held {held}s")
                _finalize(c, pos, "grad_noroute", None, None, sol_usd)
            else:
                store.log(c, pos["mint"], "grad_sold",
                          f"{pos['variant']} {lam/1e9:.4f} SOL after {tries} "
                          f"poll(s), held {held}s")
                _finalize(c, pos, "graduated", None, None, sol_usd,
                          sol_out_lam=lam)
            continue
        _last_reserves[pid] = (st["v_sol"], st["v_tok"])   # cache live reserves
        entry_px = pos["entry_v_sol"] / pos["entry_v_tok"]
        cur_px = st["v_sol"] / st["v_tok"] if st["v_tok"] else 0
        ret = (cur_px / entry_px - 1.0) if entry_px else 0.0
        if pos["variant"] in config.NOFILTER_VARIANTS:
            # FIXED-HOLD book: no TP, no stop — it exits on the clock below (or
            # on graduation / delist). The measured v3 rule was a flat 15min.
            pass
        elif pos["variant"] in config.BRACKET_VARIANTS:
            # BRACKET: take profit at +TP, HARD STOP at -SL (whichever first).
            if ret >= config.BRACKET_TP_PCT:
                _last_reserves.pop(pid, None)
                _finalize(c, pos, "take_profit", st["v_sol"], st["v_tok"], sol_usd)
                continue
            if ret <= -config.BRACKET_STOP_PCT:
                _last_reserves.pop(pid, None)
                _finalize(c, pos, "stop_loss", st["v_sol"], st["v_tok"], sol_usd)
                continue
        elif entry_px and cur_px / entry_px >= config.TP_MULT:   # legacy no-stop
            _last_reserves.pop(pid, None)
            _finalize(c, pos, "take_profit", st["v_sol"], st["v_tok"], sol_usd)
            continue
        if _deadline_passed(pos, now):
            _last_reserves.pop(pid, None)
            _finalize(c, pos, "timeout", st["v_sol"], st["v_tok"], sol_usd)
            continue
        # NO STOP: a loser rides to timeout / graduation / delist.


def exit_position(c, pos, reason, sol_usd):
    """Close ONE open position now, at the current curve fill. Used by the d60m
    mirror exit when the signal wallet sells (reason='cohort_exit'). Prices the
    same three states manage() does: account gone (rug -> -100), graduated
    (migration price), or live (current reserves)."""
    pid = pos["id"]
    st = helius.curve_state(pos["bonding_curve_key"])
    if st is None:                       # curve gone -> we can't sell either
        _last_reserves.pop(pid, None)
        _finalize(c, pos, reason, None, None, sol_usd)
    elif st["complete"]:                 # migrated -> curve locked, quote it
        _last_reserves.pop(pid, None)
        lam, status = jup.sell_quote(pos["mint"], pos["tokens"])
        if status == "ok":
            _finalize(c, pos, "graduated", None, None, sol_usd, sol_out_lam=lam)
        else:
            _finalize(c, pos, "grad_noroute", None, None, sol_usd)
    else:                                # live -> exit at current reserves
        _last_reserves.pop(pid, None)
        _finalize(c, pos, reason, st["v_sol"], st["v_tok"], sol_usd)
