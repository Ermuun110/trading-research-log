"""Draws the README figures as static SVG (light + dark), Python stdlib only.

The bar and line panels use recorded results from the research log. The equity curve is
drawn from data/meme_tier_walkforward_daily.csv. Run:  python3 docs/figures.py
"""
import csv
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

THEMES = {
    "light": dict(surface="#fcfcfb", border="#e3e2dd", grid="#ecebe7", axis="#c9c8c2",
                  ink="#0b0b0b", ink2="#52514e", ink3="#85847d", s1="#2a78d6", s2="#eb6834"),
    "dark": dict(surface="#1a1a19", border="#34342f", grid="#2a2a28", axis="#4a4a45",
                 ink="#ffffff", ink2="#c3c2b7", ink3="#8f8e86", s1="#3987e5", s2="#d95926"),
}


def text(x, y, s, fill, size=12, weight=400, anchor="start", extra=""):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" {extra}>{s}</text>')


def frame(w, h, t, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="{FONT}" role="img" aria-label="{title}">'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" fill="{t["surface"]}" '
            f'stroke="{t["border"]}"/>' + "".join(body) + "</svg>")


def hbar(x0, x1, y, th, fill, r=4):
    """Horizontal bar from the baseline x0 to x1: square at the baseline, rounded at the data end."""
    if abs(x1 - x0) < r:
        return f'<rect x="{min(x0, x1):.1f}" y="{y:.1f}" width="{abs(x1 - x0):.1f}" height="{th}" fill="{fill}"/>'
    d = 1 if x1 > x0 else -1
    return (f'<path d="M{x0:.1f},{y:.1f} H{x1 - d * r:.1f} Q{x1:.1f},{y:.1f} {x1:.1f},{y + r:.1f} '
            f'V{y + th - r:.1f} Q{x1:.1f},{y + th:.1f} {x1 - d * r:.1f},{y + th:.1f} H{x0:.1f} Z" fill="{fill}"/>')


def legend(x, y, items, t):
    out = []
    for label, color in items:
        out.append(f'<rect x="{x}" y="{y - 9}" width="10" height="10" rx="2" fill="{color}"/>')
        out.append(text(x + 16, y, label, t["ink2"], 12))
        x += 30 + 6.4 * len(label)
    return out


# ---------------------------------------------------------------- scoreboard
TILES = [
    ("71", "strategy families tested", "three markets, Jul to Oct 2026"),
    ("115", "pre-registrations", "rule and pass bar written first"),
    ("8", "positive after costs", "none has cleared every bar yet"),
    ("3", "real-money pilots", "all stopped at a small net loss"),
]


def scoreboard(t):
    w, h, pad, gap = 880, 132, 28, 16
    tw = (w - 2 * pad - 3 * gap) / 4
    body = []
    for i, (value, label, sub) in enumerate(TILES):
        x = pad + i * (tw + gap)
        if i:
            body.append(f'<line x1="{x - gap / 2:.1f}" y1="28" x2="{x - gap / 2:.1f}" y2="{h - 28}" '
                        f'stroke="{t["grid"]}"/>')
        body.append(text(x, 42, label, t["ink2"], 13))
        body.append(text(x, 84, value, t["ink"], 38, 600))
        body.append(text(x, 108, sub, t["ink3"], 12))
    return frame(w, h, t, body, "Scoreboard: 71 strategy families, 115 pre-registrations, "
                                "8 positive after costs, 3 real-money pilots")


# ------------------------------------------------------- leaked vs honest
BOOKS = [  # rule, cohort picked with lookahead, cohort rebuilt from prior weeks only
    ("3rd wallet in, wallet rested 6 h+", 8.13, -0.73),
    ("3rd wallet in", 6.09, -1.16),
    ("4th wallet in", 7.35, -0.72),
    ("5th wallet in", 8.25, 0.22),
    ("4th+ in, rested, deep curve", 9.66, 2.97),
]


def leaked_vs_honest(t):
    w, left, right, top = 880, 268, 64, 112
    row, th = 46, 12
    h = top + row * len(BOOKS) + 46
    lo, hi = -2.0, 10.0
    sx = lambda v: left + (v - lo) / (hi - lo) * (w - left - right)
    body = [text(28, 38, "Wallet-following rules: original wallet list vs rebuilt list", t["ink"], 17, 600),
            text(28, 60, "Mean return per trade (%). Rebuilt list: 11 out-of-sample weeks, 89,262 entries.",
                 t["ink2"], 13)]
    body += legend(28, 88, [("Original list (picked using the test weeks)", t["s1"]),
                            ("List rebuilt from earlier weeks only", t["s2"])], t)
    y1 = top + row * len(BOOKS) - 6
    for g in (-2, 0, 2, 4, 6, 8, 10):
        col = t["axis"] if g == 0 else t["grid"]
        body.append(f'<line x1="{sx(g):.1f}" y1="{top - 8}" x2="{sx(g):.1f}" y2="{y1}" stroke="{col}"/>')
        body.append(text(sx(g), y1 + 20, f"{g:+d}%" if g else "0", t["ink3"], 12, anchor="middle"))
    for i, (rule, leaked, honest) in enumerate(BOOKS):
        y = top + i * row
        body.append(text(28, y + 17, rule, t["ink"], 13))
        for j, (v, col) in enumerate(((leaked, t["s1"]), (honest, t["s2"]))):
            yy = y + j * (th + 2)
            body.append(hbar(sx(0), sx(v), yy, th, col))
            anchor, dx = ("start", 6) if v >= 0 else ("end", -6)
            body.append(text(sx(v) + dx, yy + 10, f"{v:+.2f}", t["ink2"], 12, anchor=anchor,
                             extra='font-variant-numeric="tabular-nums"'))
    return frame(w, h, t, body, "Five wallet-following rules: +6 to +10 percent per trade with a wallet "
                                "list picked with lookahead, -1.2 to +3.0 percent with an honest list")


# ------------------------------------------------- selection persistence
HELD = [1, 4, 8]
PANELS = [
    ("Return spread vs all wallets (pp)", 0, 16, [0, 4, 8, 12, 16],
     [13.29, 14.24, 12.09], [2.71, 3.24, 2.37], "{:+.1f}"),
    ("Wallets still trading (%)", 0, 100, [0, 25, 50, 75, 100],
     [77.5, 57.1, 50.0], [69.5, 57.5, 48.7], "{:.0f}%"),
]


def persistence(t):
    w, h, top, bottom = 880, 372, 132, 52
    pw, gap, left = 330, 96, 60
    body = [text(28, 38, "Wallets picked on past returns vs a placebo group, 1 to 8 weeks later", t["ink"], 17, 600),
            text(28, 60, "Wallet list frozen, then read forward with no re-pick. 4.14M wallets, 19 weeks.",
                 t["ink2"], 13)]
    body += legend(28, 88, [("Wallets selected on past returns", t["s1"]),
                            ("Placebo: same activity filters, no return filter", t["s2"])], t)
    for p, (title, lo, hi, ticks, sel, plc, fmt) in enumerate(PANELS):
        x0 = left + p * (pw + gap)
        sx = lambda wk: x0 + (wk - 0.5) / 8.0 * pw
        sy = lambda v: h - bottom - (v - lo) / (hi - lo) * (h - bottom - top)
        body.append(text(x0, top - 16, title, t["ink"], 13, 600))
        for g in ticks:
            col = t["axis"] if g == lo else t["grid"]
            body.append(f'<line x1="{x0}" y1="{sy(g):.1f}" x2="{x0 + pw}" y2="{sy(g):.1f}" stroke="{col}"/>')
            body.append(text(x0 - 8, sy(g) + 4, str(g), t["ink3"], 12, anchor="end"))
        for wk in HELD:
            body.append(text(sx(wk), h - bottom + 20, f"{wk} wk", t["ink3"], 12, anchor="middle"))
        body.append(text(x0 + pw / 2, h - bottom + 40, "weeks held without re-picking", t["ink3"], 12,
                         anchor="middle"))
        ends = []
        for vals, col in ((plc, t["s2"]), (sel, t["s1"])):
            pts = " ".join(f"{sx(wk):.1f},{sy(v):.1f}" for wk, v in zip(HELD, vals))
            body.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" '
                        f'stroke-linejoin="round" stroke-linecap="round"/>')
            for wk, v in zip(HELD, vals):
                body.append(f'<circle cx="{sx(wk):.1f}" cy="{sy(v):.1f}" r="5" fill="{col}" '
                            f'stroke="{t["surface"]}" stroke-width="2"/>')
            ends.append([sy(vals[-1]) + 4, fmt.format(vals[-1])])
        if abs(ends[0][0] - ends[1][0]) < 15:  # end labels would collide: keep one, name both
            hi_y = min(ends[0][0], ends[1][0])
            body.append(text(sx(8) + 12, hi_y, f"{ends[1][1]} / {ends[0][1]}", t["ink2"], 12))
        else:
            for yy, s in ends:
                body.append(text(sx(8) + 12, yy, s, t["ink2"], 12))
    return frame(w, h, t, body, "Selected wallets keep a +12 to +14 point return spread for 8 weeks while "
                                "half of them stop trading, at the same rate as a placebo group")


# ------------------------------------------------------------- era equity curve
def era_curve(t):
    path = os.path.join(os.path.dirname(OUT), "..", "data", "meme_tier_walkforward_daily.csv")
    with open(path) as f:
        rows = [(r["date"], float(r["net"])) for r in csv.DictReader(f)]
    cum, total = [], 0.0
    for _, v in rows:
        total += v * 100.0
        cum.append(total)
    w, h, left, right, top, bottom = 880, 400, 64, 76, 96, 44
    lo, hi = -250.0, 200.0
    n = len(rows)
    sx = lambda i: left + i / (n - 1) * (w - left - right)
    sy = lambda v: h - bottom - (v - lo) / (hi - lo) * (h - bottom - top)
    body = [text(28, 38, "Meme perp long/short model, cumulative return (retrained monthly)", t["ink"], 17, 600),
            text(28, 60, "Every month is out of sample. After costs and funding, % of one side of the book.", t["ink2"], 13)]
    for g in (-200, -100, 0, 100, 200):
        col = t["axis"] if g == 0 else t["grid"]
        body.append(f'<line x1="{left}" y1="{sy(g):.1f}" x2="{w - right}" y2="{sy(g):.1f}" stroke="{col}"/>')
        body.append(text(left - 8, sy(g) + 4, f"{g:+d}%" if g else "0", t["ink3"], 12, anchor="end"))
    for i, (d, _) in enumerate(rows):
        if d.endswith("-01-01"):
            body.append(text(sx(i), h - bottom + 20, d[:4], t["ink3"], 12, anchor="middle"))
    split = next(i for i, (d, _) in enumerate(rows) if d >= "2025-09-01")
    body.append(f'<line x1="{sx(split):.1f}" y1="{top - 6}" x2="{sx(split):.1f}" y2="{h - bottom}" '
                f'stroke="{t["axis"]}"/>')
    body.append(text(sx(split) - 8, top + 8, "earlier history, tested later", t["ink2"], 12, anchor="end"))
    body.append(text(sx(split) + 8, top + 8, "research year", t["ink2"], 12))
    body.append(text(sx(split) - 8, top + 26, "-20.6 bp a day, Sharpe -1.4", t["ink3"], 12, anchor="end"))
    body.append(text(sx(split) + 8, top + 26, "+97 bp a day, Sharpe 3.1", t["ink3"], 12))
    pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(cum))
    body.append(f'<polyline points="{pts}" fill="none" stroke="{t["s1"]}" stroke-width="2" '
                f'stroke-linejoin="round" stroke-linecap="round"/>')
    body.append(f'<circle cx="{sx(n - 1):.1f}" cy="{sy(cum[-1]):.1f}" r="5" fill="{t["s1"]}" '
                f'stroke="{t["surface"]}" stroke-width="2"/>')
    body.append(text(sx(n - 1) + 12, sy(cum[-1]) + 4, f"{cum[-1]:+.0f}%", t["ink2"], 12))
    return frame(w, h, t, body, "Cumulative return of the meme-tier book: falls about 200 points over "
                                "2023 to 2025, then rises about 390 points in 2026")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("scoreboard", scoreboard), ("leaked-vs-honest", leaked_vs_honest),
                     ("selection-persistence", persistence), ("era-curve", era_curve)):
        for mode, theme in THEMES.items():
            with open(os.path.join(OUT, f"{name}-{mode}.svg"), "w") as f:
                f.write(fn(theme))
    print("wrote", sorted(os.listdir(OUT)))
