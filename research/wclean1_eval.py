"""PREREG-WCLEAN1 step 2: the five frozen 41b configs x list age L x clean-wallet filter x period. Prints the full table and
applies the pre-registered pick (P1, headline, L=24) and confirm (P2) mechanically. Reads nothing from the tape."""
import numpy as np, pandas as pd, duckdb, glob, json, sys, time
sys.path.insert(0, 'research/scratch/2026-09-27-launch')
from common import SP, P1_END, P2_END
from l19_freq_grid import roll, qual, pick, stats, lab, M0
HERE = 'research/scratch/2026-09-27-launch'
PA = 'data/work/solcopy/pa'
FEE, W = 0.0176, 28
T = time.time()


def load9():
    parts = []
    for fp in sorted(glob.glob(SP + '/we/ev*.npz')):
        k = fp.split('/ev')[-1][:-4]
        E = np.load(fp); R = np.load(f'data/work/solcopy/r9/r9_{k}.npy')
        df = pd.DataFrame({'id': E['id'], 'w': E['w'], 'tb': E['tb'], 'sb': E['sb'].astype(np.float32), 'r9': R.astype(np.float32)})
        pa = duckdb.sql(f"SELECT id, w, sol_in, sol_out, nre, own300, coin300 FROM '{PA}/pa{k}.parquet'").df()
        pa['w'] = pa['w'].astype(np.uint64); pa['id'] = pa['id'].astype(np.int32)
        df = df.merge(pa, on=['id', 'w'], how='left')
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


def rsum(wi, dref, sday, x, W):
    """sum of x over the wallet's events with stat-day in [dref - W, dref)."""
    key = wi * 100000 + sday
    order = np.argsort(key, kind='stable'); ks = key[order]
    uk, first = np.unique(ks, return_index=True); idx = np.append(first, len(ks))
    c = np.concatenate([[0], np.cumsum(x[order])])[idx]
    return c[np.searchsorted(uk, wi * 100000 + dref, 'left')] - c[np.searchsorted(uk, wi * 100000 + dref - W, 'left')]


D = load9().sort_values('tb', kind='stable').reset_index(drop=True)
print('events', len(D), 'pair facts missing', int(D.sol_in.isna().sum()), f'{time.time()-T:.0f}s', flush=True)
cash = (D.sol_out.values * (1 - FEE) - D.sol_in.values * (1 + FEE)); cash = np.nan_to_num(cash)
lad = (D.nre.fillna(0).values > 0).astype(float)
dom = ((D.coin300.fillna(0).values > 0) & (D.own300.fillna(0).values >= 0.5 * D.coin300.fillna(0).values)).astype(float)
print(f'event base rates: ladder {lad.mean():.3f}  dominant {dom.mean():.3f}  cash>0 {(cash > 0).mean():.3f}  mean cash {cash.mean():+.4f} SOL', flush=True)
wi = pd.factorize(D.w)[0].astype(np.int64); day = (D.tb.values // 86400).astype(np.int64)
sday = ((D.tb.values + 1800) // 86400).astype(np.int64); sdc = ((D.tb.values + 7200) // 86400).astype(np.int64)
v = D.r9.values.astype(np.float64); ok = np.isfinite(v); one = np.ones(len(D))
cfgs = json.load(open(HERE + '/frozen_W11.json'))
PER = {'P1': (D.tb.values >= M0) & (D.tb.values < P1_END), 'P2': (D.tb.values >= P1_END) & (D.tb.values < P2_END)}
rows = []
for L in (0, 7, 14, 24):
    st_all = roll(wi, day - L, sday, v, ok, W)
    nc = rsum(wi, day - L, sdc, one, W); c28 = rsum(wi, day - L, sdc, cash, W)
    with np.errstate(invalid='ignore', divide='ignore'):
        ls = rsum(wi, day - L, sdc, lad, W) / nc; ds = rsum(wi, day - L, sdc, dom, W) / nc
    C1 = (nc > 0) & (c28 > 0); C2 = (nc > 0) & (ls <= 0.20); C3 = (nc > 0) & (ds <= 0.20); C4 = C1 & C2 & C3
    F = {'none': np.ones(len(D), bool), 'C1': C1, 'C2': C2, 'C3': C3, 'C4': C4, 'X': ~C4}
    for pn, mask in PER.items():
        P = D.loc[mask, ['id', 'tb', 'sb', 'r9']].reset_index(drop=True)
        days = pd.date_range(pd.to_datetime(P.tb.min(), unit='s').floor('D'), pd.to_datetime(P.tb.max(), unit='s').floor('D'), freq='D')
        st = tuple(a[mask] for a in st_all); okp = np.isfinite(P.r9.values.astype(float))
        for ci, cf in enumerate(cfgs):
            q0 = qual(st, cf['sc']) & okp
            for fn, fm in F.items():
                x = pick(P, q0 & fm[mask], cf['c'], cf['sb'])
                s = stats(x.r9.values.astype(float), x.tb.values, days)
                rows.append(dict(L=L, per=pn, cfg=ci, filt=fn, n=s.get('n', 0), perday=s.get('perday', 0), mean=s.get('mean', np.nan),
                                 med=s.get('med', np.nan), sumt=s.get('sumt', np.nan), top3=s.get('top3', np.nan), win=s.get('win', np.nan)))
    print('L', L, f'{time.time()-T:.0f}s', flush=True)
G = pd.DataFrame(rows); G.to_csv('data/work/solcopy/wclean_grid.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
for ci, cf in enumerate(cfgs):
    print('\n== cfg', ci, lab(cf))
    for pn in ('P1', 'P2'):
        g = G[(G.cfg == ci) & (G.per == pn)]
        for col in ('mean', 'sumt', 'perday', 'med'):
            print(pn, col); print(g.pivot(index='filt', columns='L', values=col).reindex(['none', 'C1', 'C2', 'C3', 'C4', 'X']).round(2).to_string())
H = 3
p1 = G[(G.cfg == H) & (G.per == 'P1') & (G.L == 24) & (G.filt.isin(['C1', 'C2', 'C3', 'C4'])) & (G.perday >= 5)].sort_values('sumt', ascending=False)
print('\nPICK (P1, headline, L=24):'); print(p1[['filt', 'n', 'perday', 'mean', 'med', 'sumt']].round(2).to_string())
if len(p1):
    fs = p1.iloc[0].filt
    c = G[(G.per == 'P2') & (G.L == 24) & (G.filt == fs)]; h = c[c.cfg == H].iloc[0]
    base = G[(G.per == 'P2') & (G.L == 24) & (G.filt == 'none') & (G.cfg == H)].iloc[0]
    bars = {'mean>=2': h['mean'] >= 2, 'sumt>=2.5': h.sumt >= 2.5, 'top3<.5': h.top3 < 0.5, 'n>=300': h.n >= 300,
            '>=4/5 cfg mean>0': int((c['mean'] > 0).sum()) >= 4, 'beats unfiltered mean': h['mean'] > base['mean']}
    print(f"\nF* = {fs}. CONFIRM P2 L=24 headline: n {h.n} n/day {h.perday:.1f} mean {h['mean']:+.2f}% med {h.med:+.2f}% sum-t {h.sumt:.2f} "
          f"top3 {h.top3:.2f} | unfiltered mean {base['mean']:+.2f}% sum-t {base.sumt:.2f}")
    print(bars); print('VERDICT:', 'PASS -> tape read allowed' if all(bars.values()) else 'FAIL -> tape NOT read')
else:
    print('no filter has >= 5 trades/day on P1 at L=24: FAIL')
