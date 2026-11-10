# Getting the data

Raw files are not committed (about 300 MB). Download them from [data.ok.gov](https://data.ok.gov):

1. Search for **"Purchase Card (PCard) Fiscal Year"** and open the FY2023 to FY2027 datasets.
2. Download the monthly files named `pcard_public_YYYYMM.csv` (some have suffixes such as `_without-row-id`).
3. Put them anywhere under `data/raw/` (subfolders are fine).

Do **not** use the `county-p-card-spend` files. They look similar but cover only counties and a few programs.

## Known problems in the source files

`src/load.py` handles all of these automatically and writes a per-file report to `results/data_audit.csv`.

- **Names that do not match contents.** The month in a file name is not reliable. For example, `pcard_public_202505.csv` contains April 2025 transactions, and one of the files named `pcard_public_202606...` contains May 2026. Every row is assigned to a month by its posting date.
- **Duplicate uploads.** Several months exist as two byte-identical files; duplicates are dropped.
- **Header and format drift.** Some files pad the `AMOUNT` header with spaces, add or remove a `ROWID` column, or start with a byte-order mark.
- **Gaps.** No statewide file was available for May 2025 or January 2026.
