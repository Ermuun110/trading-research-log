"""g13: EXACT end-of-slot state via reserve chaining (pre_vtok = vtok +/- token_amount; the slot's last trade is the one
whose post-vtok is no other trade's pre-vtok). Ambiguous slots fall back to worst case (entry hi / exit lo). Was g12: g6 rerun with WORST-CASE intra-slot ties for every as-of state (the data has no order inside a slot; the
arg_max(mc, slot*1e6+ts) as-of picked an arbitrary trade of a tied slot). Original g6 numbers printed alongside.
Original doc: Slot-latency sweep for the confluence cell. Signal = 2nd followable wallet's buy (selection identical to g5).
Entry = WORST (max mc) of: curve state as of landing slot s+K, and every trade inside slot s+K.
Exit triggers from trades after the landing slot; exit fill = WORST (min mc) in slot trigger+K. 0.3 SOL, 1.45% fee."""
import duckdb, numpy as np, pandas as pd, sys, time
src = open('g5_judge.py').read(); exec(src.split("p = 'u200_d50_t300'")[0])     # R + cell()
P = 'u200_d50_t300'
S, _ = cell(P, 0.6, 10, 2, 600)
ev = S[['id', 'w', 'ts', 'te', 'P1']].copy()
DB = 'scratch/launch.duckdb'
SP = 'scratch'
c = duckdb.connect(DB)
for s in ("SET temp_directory='scratch/duck'", "SET memory_limit='12GB'", "SET threads=8"):
    c.execute(s)
c.execute(f"ATTACH '{SP}/b.duckdb' AS b (READ_ONLY)")
c.register('evdf', ev)
c.execute("CREATE OR REPLACE TABLE sev AS SELECT e.*, t.slot s0 FROM evdf e JOIN b.t t ON t.id=e.id AND t.w=e.w AND t.ts=e.ts AND t.buy QUALIFY row_number() OVER (PARTITION BY e.id ORDER BY t.slot)=1")
print('signal events', c.execute('select count(*) from sev').fetchone(), flush=True)
c.execute("CREATE OR REPLACE TABLE tr AS SELECT t.id, t.slot, t.ts, t.mc FROM b.t t SEMI JOIN sev USING(id)")
SIZE, TIP, FEE = 0.3, 0.001, 0.0145
cost = lambda mc: FEE + SIZE / np.sqrt(np.maximum(mc, 1) * 32.19) + TIP / SIZE
out = []
c.execute("SET temp_directory='scratch/duck'; SET max_temp_directory_size='40GB'")
c.execute("CREATE OR REPLACE TEMP TABLE sm AS SELECT DISTINCT m.mint, m.id FROM b.m m SEMI JOIN sev ON sev.id=m.id")
c.execute("""CREATE OR REPLACE TABLE ax AS SELECT sm.id, e.slot, e.ts, e.vtok, e.token_amount tok, e.action='buy' buy,
    e.vlam::DOUBLE*1e6/e.vtok::DOUBLE mc
    FROM 'data/cache/pregrad/archive_events.parquet' e JOIN sm ON sm.mint=e.mint
    WHERE e.event_type='swap' AND e.vtok > 0""")
print('ax', c.execute('select count(*), count(distinct id) from ax').fetchone(), flush=True)
c.execute("""CREATE OR REPLACE TABLE fin AS WITH p AS (SELECT *, CASE WHEN buy THEN vtok + tok ELSE vtok - tok END pre FROM ax),
    cand AS (SELECT p.* FROM p WHERE NOT EXISTS (SELECT 1 FROM p q WHERE q.id=p.id AND q.slot=p.slot AND q.pre=p.vtok
                                                  AND NOT (q.vtok=p.vtok AND q.pre=p.pre)))
    SELECT id, slot, count(*) nc, min(mc) cmin, max(mc) cmax FROM cand GROUP BY 1, 2""")
c.execute("""CREATE OR REPLACE TABLE tsl AS SELECT a.id, a.slot, max(a.mc) hi, min(a.mc) lo, count(*) n,
    any_value(f.nc) nc, any_value(CASE WHEN f.nc=1 THEN f.cmax END) ex FROM ax a LEFT JOIN fin f USING(id, slot) GROUP BY 1, 2""")
print('slots', c.execute("select count(*), sum((n>1)::INT), sum((n>1 and nc=1)::INT), sum((n>1 and coalesce(nc,0)<>1)::INT) from tsl").fetchone(),
      '(all, multi-trade, multi exact, multi ambiguous)', flush=True)
c.execute("CREATE OR REPLACE TABLE tsl AS SELECT *, coalesce(ex, hi) he, coalesce(ex, lo) le FROM tsl")
for K in (2, 3, 4):
    c.execute(f"""CREATE OR REPLACE TABLE en AS SELECT sev.id, sev.P1, sev.te, sev.s0+{K} sl,
        greatest(coalesce((SELECT max(mc) FROM tr WHERE tr.id=sev.id AND tr.slot=sev.s0+{K}), 0),
                 (SELECT arg_max(he, slot) FROM tsl WHERE tsl.id=sev.id AND tsl.slot<=sev.s0+{K})) mce,
        (SELECT min(ts) FROM tr WHERE tr.id=sev.id AND tr.slot=sev.s0+{K}) tsl
        FROM sev""")
    D = c.execute(f"""WITH x AS (SELECT en.*, coalesce(tsl, te) t_in FROM en),
      trg AS (SELECT x.id, min(tr.slot) FILTER (WHERE tr.mc >= 2*x.mce) su, min(tr.slot) FILTER (WHERE tr.mc <= 0.5*x.mce) sd,
                     max(tr.slot) FILTER (WHERE tr.ts <= x.t_in+300) sto
              FROM x JOIN tr ON tr.id=x.id AND tr.slot > x.sl AND tr.ts <= x.t_in+300 GROUP BY 1)
      SELECT x.id, x.P1, x.te, x.mce, trg.su, trg.sd, trg.sto,
        (SELECT min(mc) FROM tr WHERE tr.id=x.id AND tr.slot=trg.su+{K}) fu_in, (SELECT arg_max(le, slot) FROM tsl WHERE tsl.id=x.id AND tsl.slot<=trg.su+{K}) fu_as,
        (SELECT min(mc) FROM tr WHERE tr.id=x.id AND tr.slot=trg.sd+{K}) fd_in, (SELECT arg_max(le, slot) FROM tsl WHERE tsl.id=x.id AND tsl.slot<=trg.sd+{K}) fd_as,
        (SELECT arg_max(le, slot) FROM tsl WHERE tsl.id=x.id AND tsl.slot<=(SELECT max(slot) FROM tr t2 WHERE t2.id=x.id AND t2.ts<=x.t_in+300)) fto
      FROM x LEFT JOIN trg USING(id)""").df()
    su = D.su.astype(float).fillna(np.inf); sd = D.sd.astype(float).fillna(np.inf)
    fu = np.fmin(D.fu_in.astype(float).fillna(np.inf), D.fu_as.astype(float)); fd = np.fmin(D.fd_in.astype(float).fillna(np.inf), D.fd_as.astype(float))
    px = np.where((su < sd) & (su < np.inf), fu, np.where(sd < np.inf, fd, D.fto.fillna(D.mce)))
    D['ret'] = px / D.mce * (1 - cost(px)) / (1 + cost(D.mce)) - 1
    for lab, d in (('P1 Apr-Jun', D[D.P1]), ('confirm Jul-Aug', D[~D.P1])):
        out.append((K, lab, len(d), d.ret.mean(), d.ret.median(), (d.ret > 0).mean()))
    print(K, [f'{o[1]} mean {o[3]*100:+.2f}% med {o[4]*100:+.2f}% win {o[5]:.2f}' for o in out[-2:]], flush=True)
    D.to_pickle(f'g13_K{K}.pkl')
    O = pd.read_pickle(f'g6_K{K}.pkl')
    for lab, m in (('P1 Apr-Jun', O.P1), ('confirm Jul-Aug', ~O.P1)):
        print('   original g6', K, lab, f'mean {O.ret[m].mean()*100:+.2f}% med {O.ret[m].median()*100:+.2f}%', flush=True)
    j = D.merge(O[['id', 'ret']], on='id', suffixes=('', '_g6'))
    print('   changed rows', int(((j.ret - j.ret_g6).abs() > 1e-9).sum()), 'of', len(j), flush=True)
