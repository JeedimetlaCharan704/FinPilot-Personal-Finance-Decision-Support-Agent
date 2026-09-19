"""Generate data/demo_data.csv deterministically (Phase 3)."""
from pathlib import Path

from app.services.demo_data import generate_transactions, write_csv

ROOT = Path(__file__).resolve().parents[1]  # apps/api/scripts -> repo root... actually -> apps/api?
# apps/api/scripts -> repo root is parents[2]
ROOT2 = Path(__file__).resolve().parents[3]
CSV = ROOT2 / "data" / "demo_data.csv"

if __name__ == "__main__":
    rows = generate_transactions(seed=2026, month_count=6)
    write_csv(CSV, rows)
    print(f"Wrote {len(rows)} rows to {CSV}")