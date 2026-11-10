"""Load Oklahoma P-card monthly files, fix labelling problems, and save one clean table.

The portal's files are inconsistent: some names do not match their contents (e.g. a file named
`pcard_public_202505.csv` holds April 2025), some months were uploaded twice, and headers vary.
We therefore (1) drop byte-identical duplicate files, (2) assign every row to a month using its
posting date rather than the file name, and (3) drop exact duplicate transactions.
"""
import hashlib
import numpy as np
import pandas as pd
from config import RAW_DIR, PROCESSED, RESULTS, HIGHER_ED_PATTERN


def _money(s):
    s = s.astype(str).str.replace(r"[\$,\s]", "", regex=True).str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    return pd.to_numeric(s, errors="coerce")


def _date(s):
    s = s.astype(str).str.strip()
    out = pd.to_datetime(s, format="%d-%b-%y", errors="coerce")
    for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%Y-%m-%d %H:%M:%S"]:
        out = out.fillna(pd.to_datetime(s, format=fmt, errors="coerce"))
    return out


def load():
    paths = sorted(p for p in RAW_DIR.rglob("pcard_public_*.csv") if "__MACOSX" not in p.parts)
    if not paths:
        raise SystemExit(f"No pcard_public_*.csv files found under {RAW_DIR}. See data/README.md.")
    frames, audit, seen = [], [], {}
    for p in paths:
        digest = hashlib.md5(p.read_bytes()).hexdigest()
        df = pd.read_csv(p, dtype=str, encoding="latin1")
        df.columns = [c.replace("﻿", "").replace("ï»¿", "").strip().upper() for c in df.columns]
        d = pd.DataFrame({
            "agency": df.AGENCYNBR.str.strip().str.zfill(5),
            "unit": (df.AGENCYNBR.str.strip() + " " + df.AGENCYNAME.str.strip()).str.upper(),
            "last": df.LAST_NAME.fillna("").str.strip().str.upper(),
            "first": df.FIRST_INITIAL.fillna("").str.strip().str.upper(),
            "amount": _money(df.AMOUNT),
            "merchant": df.MERCHANT.fillna("").str.strip().str.upper(),
            "mcc": df.MCC_DESCRIPTION.fillna("").str.strip().str.upper(),
            "date": _date(df.TRANSACTION_DATE),
            "post": _date(df.POST_DATE),
        })
        month = d.post.dt.to_period("M").mode()
        dup_of = seen.get(digest)
        seen.setdefault(digest, p.name)
        audit.append(dict(file=p.name, rows=len(d), month_in_data=str(month.iloc[0]) if len(month) else "",
                          duplicate_of=dup_of or "", unparsed_amounts=int(d.amount.isna().sum()),
                          unparsed_dates=int(d.date.isna().sum())))
        if not dup_of:
            frames.append(d)
    a = pd.concat(frames, ignore_index=True)
    n0 = len(a)
    a = a.drop_duplicates(["agency", "last", "first", "amount", "merchant", "date", "post"])
    a = a[(a.amount > 0) & a.post.notna()].copy()
    a["higher_ed"] = a.unit.str.contains(HIGHER_ED_PATTERN, regex=True)
    a["cardholder"] = a.agency + "|" + a["last"] + "|" + a["first"]
    a["month"] = a.post.dt.to_period("M")
    a.to_pickle(PROCESSED)
    RESULTS.mkdir(exist_ok=True)
    pd.DataFrame(audit).to_csv(RESULTS / "data_audit.csv", index=False)
    cov = a.groupby("month").size()
    all_months = pd.period_range(cov.index.min(), cov.index.max(), freq="M")
    missing = [str(m) for m in all_months if m not in cov.index]
    print(f"{len(paths)} files, {sum(1 for r in audit if r['duplicate_of'])} duplicates dropped; "
          f"{n0:,} rows -> {len(a):,} after de-duplication; months {cov.index.min()}..{cov.index.max()}; missing {missing}")
    return a


if __name__ == "__main__":
    load()
