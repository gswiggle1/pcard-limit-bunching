"""Run every analysis in the README and write results/*.csv plus results/summary.json."""
import json
import numpy as np
import pandas as pd
from config import (PROCESSED, RESULTS, OLD_LIMIT, NEW_LIMIT, POLICY_DATE, ODOT, PLACEBOS,
                    EXEMPT_MCC_PATTERN, SEED)
from bunching import bunching_at

near = lambda s: (s >= 4800) & (s < 5000)
base = lambda s: (s >= 4000) & (s < 4800)


def groups(a):
    ag = a[~a.higher_ed]
    return {"All state agencies": ag, "Agencies excl. ODOT": ag[ag.agency != ODOT],
            "ODOT": ag[ag.agency == ODOT], "Universities": a[a.higher_ed]}


def pooled_bunching(a):
    rows = []
    for g, sub in groups(a).items():
        for per in ["pre", "post"]:
            s = sub[sub.period == per].amount.values
            for T in [OLD_LIMIT, NEW_LIMIT] + PLACEBOS:
                r = bunching_at(s, T, seed=SEED)
                r.update(group=g, period=per, placebo=T in PLACEBOS)
                rows.append(r)
    return pd.DataFrame(rows)


def changes(b):
    out = []
    for (g, T), z in b.groupby(["group", "threshold"]):
        p, q = z[z.period == "pre"].iloc[0], z[z.period == "post"].iloc[0]
        d, se = q.per100k - p.per100k, np.hypot(p.se_per100k, q.se_per100k)
        out.append(dict(group=g, threshold=T, pre_per100k=p.per100k, post_per100k=q.per100k,
                        change=d, se=se, z=d / se, pct_change=100 * d / p.per100k if p.per100k else np.nan))
    return pd.DataFrame(out)


def quarterly(a):
    rows = []
    a = a.assign(q=a.post.dt.to_period("Q"))
    for g, sub in groups(a).items():
        for q, z in sub.groupby("q"):
            s = z.amount
            b = base(s).sum() / 4
            rows.append(dict(group=g, quarter=str(q), n=len(s), near=int(near(s).sum()),
                             bunching_ratio=near(s).sum() / b if b else np.nan,
                             ge5k_per1k=(s >= OLD_LIMIT).mean() * 1e3))
    return pd.DataFrame(rows)


def split_clusters(a, window_days=3):
    """Same cardholder + same merchant, 2-4 charges within `window_days`, each under $5k,
    largest at least $2k, summing to $5k-$15k, excluding cap-exempt merchant categories."""
    z = a.copy()
    z["m"] = z.merchant.str.replace(r"[^A-Z]", "", regex=True).str[:10]
    z = z[z.m.str.len() >= 3].sort_values(["cardholder", "m", "date"])
    gap = z.groupby(["cardholder", "m"], sort=False).date.diff().dt.days
    z["cid"] = ((gap.isna()) | (gap > window_days)).cumsum()
    c = z.groupby("cid").agg(n=("amount", "size"), tot=("amount", "sum"), mx=("amount", "max"),
                             span=("date", lambda s: (s.max() - s.min()).days), mcc=("mcc", "first"))
    c["split"] = (c.n.between(2, 4) & (c.mx < OLD_LIMIT) & (c.tot > OLD_LIMIT) & (c.tot <= 3 * OLD_LIMIT)
                  & (c.span <= window_days) & (c.mx >= 0.4 * OLD_LIMIT)
                  & ~c.mcc.str.contains(EXEMPT_MCC_PATTERN, regex=True))
    return z.merge(c[["split"]], left_on="cid", right_index=True)


def split_shares(z):
    rows = []
    for g, sub in groups(z).items():
        for per in ["pre", "post"]:
            s = sub[sub.period == per]
            for band, (lo, hi) in {"$4,800-4,999 (near cap)": (4800, 5000), "$3,800-3,999 (placebo)": (3800, 4000),
                                   "$2,800-2,999 (placebo)": (2800, 3000)}.items():
                q = s[(s.amount >= lo) & (s.amount < hi)]
                p = q.split.mean()
                rows.append(dict(group=g, period=per, band=band, n=len(q), split_share=100 * p,
                                 se=100 * np.sqrt(p * (1 - p) / len(q))))
    return pd.DataFrame(rows)


def unlocked_cardholders(a, reps=400):
    """Cardholders with no non-exempt $5k-$25k charge before the change and at least one after:
    their own limit was demonstrably raised. Compare their near-cap rate change to cardholders
    who never exceeded $5k (difference-in-differences, cardholder-clustered bootstrap)."""
    ag = a[~a.higher_ed].copy()
    ag["mid"] = (ag.amount >= OLD_LIMIT) & (ag.amount < NEW_LIMIT) & ~ag.mcc.str.contains(EXEMPT_MCC_PATTERN, regex=True)
    g = ag.groupby(["cardholder", "period"]).agg(n=("amount", "size"), mid=("mid", "sum")).unstack(fill_value=0)
    both = g[(g["n", "pre"] >= 20) & (g["n", "post"] >= 20)]
    treated = both[(both["mid", "pre"] == 0) & (both["mid", "post"] >= 1)].index
    control = both[(both["mid", "pre"] == 0) & (both["mid", "post"] == 0)].index
    ag["arm"] = np.where(ag.cardholder.isin(treated), "unlocked", np.where(ag.cardholder.isin(control), "control", ""))
    z = ag[ag.arm != ""].reset_index(drop=True)

    def stat(z):
        o = {}
        for arm in ["unlocked", "control"]:
            for per in ["pre", "post"]:
                s = z[(z.arm == arm) & (z.period == per)].amount
                o[arm, per] = (near(s).sum(), base(s).sum() / 4, len(s))
        r = {k: v[0] / v[1] for k, v in o.items()}
        rate = {k: v[0] / v[2] * 1e4 for k, v in o.items()}
        did = (rate["unlocked", "post"] - rate["unlocked", "pre"]) - (rate["control", "post"] - rate["control", "pre"])
        return o, r, did

    o, r, did = stat(z)
    rng = np.random.default_rng(SEED)
    idx = z.groupby("cardholder").indices
    chs = np.array(list(idx))
    boot = [stat(z.iloc[np.concatenate([idx[c] for c in rng.choice(chs, len(chs))])])[2] for _ in range(reps)]
    s_post = z[(z.arm == "unlocked") & (z.period == "post")].amount
    nb, bb = near(s_post).sum(), base(s_post).sum() / 4
    return dict(n_unlocked=len(treated), n_control=len(control),
                ratio={f"{k[0]}_{k[1]}": v for k, v in r.items()},
                did_near_per10k=did, did_se=float(np.std(boot)),
                did_ci=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                unlocked_post_near=int(nb), unlocked_post_base_per_bin=float(bb),
                unlocked_post_z_vs_no_spike=float((nb - bb) / np.sqrt(bb)))


def odot_profile(a):
    ag = a[~a.higher_ed]
    out = {}
    for per in ["pre", "post"]:
        z = ag[ag.period == per]
        t = z.groupby("agency").amount.agg(near=lambda s: near(s).sum(), base=lambda s: base(s).sum() / 4)
        t["excess"] = t.near - t.base
        out[f"odot_share_of_excess_{per}"] = float(t.loc[ODOT, "excess"] / t.excess.sum())
    od = ag[ag.agency == ODOT]
    nc = od[near(od.amount)]
    out["odot_top_merchants"] = nc.merchant.value_counts().head(6).to_dict()
    out["odot_top_mcc"] = nc.mcc.value_counts().head(4).to_dict()
    nc_all = ag[near(ag.amount)]
    out["share_near_cap_in_last_20_dollars"] = float((nc_all.amount >= 4980).mean())
    k = nc_all.groupby("cardholder").size()
    out["share_near_cap_from_repeat_cardholders"] = float(k[k >= 3].sum() / k.sum())
    return out


def main():
    a = pd.read_pickle(PROCESSED)
    a["period"] = np.where(a.post < POLICY_DATE, "pre", "post")
    RESULTS.mkdir(exist_ok=True)
    b = pooled_bunching(a); b.to_csv(RESULTS / "bunching_pooled.csv", index=False)
    c = changes(b); c.to_csv(RESULTS / "bunching_changes.csv", index=False)
    q = quarterly(a); q.to_csv(RESULTS / "quarterly.csv", index=False)
    z = split_clusters(a); s = split_shares(z); s.to_csv(RESULTS / "split_shares.csv", index=False)
    u = unlocked_cardholders(a)
    o = odot_profile(a)
    summary = dict(
        n_transactions=int(len(a)), n_agency_txns=int((~a.higher_ed).sum()),
        months=f"{a.month.min()}..{a.month.max()}", n_cardholders=int(a.cardholder.nunique()),
        n_agencies=int(a.agency.nunique()),
        unlocked_cardholders=u, odot=o)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    pd.set_option("display.width", 220)
    print(b[["group", "period", "threshold", "n", "actual", "counterfactual", "excess", "se", "excess_pct", "per100k", "se_per100k"]].round(1).to_string(index=False))
    print(c.round(2).to_string(index=False))
    print(s.round(1).to_string(index=False))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
