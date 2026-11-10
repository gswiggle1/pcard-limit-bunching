"""Shared settings for the P-card bunching analysis."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"          # put pcard_public_*.csv files here (any subfolders)
PROCESSED = ROOT / "data" / "processed.pkl"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

OLD_LIMIT = 5_000
NEW_LIMIT = 25_000
POLICY_DATE = "2025-01-01"   # OMES raised the agency single-purchase threshold effective Jan 1, 2025
ODOT = "34500"               # Department of Transportation agency number
PLACEBOS = [3_000, 4_000, 6_000, 7_000]
SEED = 0

# Universities and colleges run their own card programs; used as a comparison group.
HIGHER_ED_PATTERN = (r"UNIV|COLLEGE|COLEGE|OUHSC| RSU|RSU$|TECHNOLOGY CENTER|N\. E\. OKLA|"
                     r"REGENTS|S\. W\. OKLA|PANHANDLE|LANGSTON|SCIENCE & ARTS")
# Merchant categories where the per-transaction cap does not apply (utilities, interagency, etc.)
EXEMPT_MCC_PATTERN = r"UTILIT|ELECTRIC|GAS|WATER|TELECOM|CABLE|GOVERNMENT SERV|INSURANCE"

PALETTE = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a",
           "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e5e4df", "surface": "#fcfcfb"}
