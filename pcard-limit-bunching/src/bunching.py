"""Bunching estimator (Chetty et al. 2011; Kleven 2016 style) for transaction amounts.

Count transactions in fixed-width bins around a threshold T, fit a flexible polynomial to the
counts *excluding* a window just below T, and read the counterfactual in that window off the fit.
Excess mass = actual - counterfactual. Round-number dummies absorb heaping at multiples of
$100/$500/$1,000. Standard errors come from a residual bootstrap.
"""
import numpy as np


def bunching(amounts, T, width=50, window=(0.5, 1.6), excluded=200, degree=7, reps=500, seed=0):
    amounts = np.asarray(amounts)
    edges = np.arange(T * window[0], T * window[1] + width, width)
    counts, _ = np.histogram(amounts, edges)
    x = edges[:-1]
    z = (x - T) / T
    X = np.column_stack([z ** k for k in range(degree + 1)] +
                        [(np.mod(x, m) == 0).astype(float) for m in (1000, 500, 100)])
    ex = (x >= T - excluded) & (x < T)
    D = np.column_stack([X] + [(x == v).astype(float) for v in x[ex]])
    beta, *_ = np.linalg.lstsq(D, counts, rcond=None)
    k = X.shape[1]
    cf = X @ beta[:k]
    excess = (counts[ex] - cf[ex]).sum()
    fit = D @ beta
    resid = counts - fit
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(reps):
        cb = fit + rng.choice(resid, len(resid), replace=True)
        bb, *_ = np.linalg.lstsq(D, cb, rcond=None)
        boot.append((cb[ex] - X[ex] @ bb[:k]).sum())
    se = float(np.std(boot))
    n = len(amounts)
    return dict(threshold=T, n=n, actual=int(counts[ex].sum()), counterfactual=float(cf[ex].sum()),
                excess=float(excess), se=float(se), excess_pct=float(100 * excess / cf[ex].sum()),
                per100k=float(excess / n * 1e5), se_per100k=float(se / n * 1e5))


def bunching_at(amounts, T, seed=0):
    """Settings used throughout: $50 bins near $5k-scale thresholds, $500 bins at $25k."""
    if T >= 20_000:
        return bunching(amounts, T, width=500, window=(0.4, 1.6), excluded=1000, degree=4, seed=seed)
    return bunching(amounts, T, seed=seed)
