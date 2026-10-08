"""Stdlib scorer for an exported sklearn HistGradientBoostingClassifier (binary).

Mirrors sklearn's _predictor.pyx exactly: the preprocessor ordinal-encodes categorical
columns and moves them first; NaN (None) follows missing_go_to_left; a negative or unknown
category is treated as missing."""
import json
import math


class GBM:
    def __init__(self, path):
        J = json.load(open(path))
        self.J = J
        self.features, self.order = J["features"], J["order"]
        self.cats = {k: {float(v): i for i, v in enumerate(vals)} for k, vals in J["cats"].items()}
        self.base = J["baseline"]
        self.trees = [(t["nodes"], t["bitsets"]) for t in J["trees"]]
        self.known, self.fmap = J["known_cat_bitsets"], J["f_idx_map"]
        self.cutoff = J["cutoff"]

    @staticmethod
    def _in(bits, v):
        return (bits[v // 32] >> (v % 32)) & 1

    def _row(self, x):
        out = []
        for f in self.order:
            v = x.get(f)
            if v is None or (isinstance(v, float) and math.isnan(v)):
                out.append(None)
            elif f in self.cats:
                out.append(self.cats[f].get(float(v)))        # unseen category -> missing
            else:
                out.append(float(v))
        return out

    def proba(self, x):
        r = self._row(x)
        raw = self.base
        for nodes, bitsets in self.trees:
            n = nodes[0]
            while not n[5]:
                fi, thr, mleft, left, right, _, _, iscat, bidx = n
                v = r[fi]
                if v is None:
                    nxt = left if mleft else right
                elif iscat:
                    c = int(v)
                    if c < 0:
                        nxt = left if mleft else right
                    elif self._in(bitsets[bidx], c):
                        nxt = left
                    elif self._in(self.known[self.fmap[fi]], c):
                        nxt = right
                    else:
                        nxt = left if mleft else right
                else:
                    nxt = left if v <= thr else right
                n = nodes[nxt]
            raw += n[6]
        return 1.0 / (1.0 + math.exp(-raw))
