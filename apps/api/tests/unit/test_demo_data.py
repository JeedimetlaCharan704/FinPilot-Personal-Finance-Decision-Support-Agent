from pathlib import Path

from app.services import demo_data


def _gen():
    return demo_data.generate_transactions(seed=2026, month_count=6)


def test_rows_generated():
    rows = _gen()
    assert rows
    assert len(rows) >= 9 * 6 + 1  # recurring + anomaly


def test_validation_clean():
    rows = _gen()
    errors = demo_data.validate_rows(rows)
    assert errors == []


def test_deterministic():
    assert _gen() == _gen()


def test_seed_changes_output():
    a = demo_data.generate_transactions(seed=2026)
    b = demo_data.generate_transactions(seed=999)
    assert a != b


def test_validation_catches_bad_rows():
    rows = _gen()
    rows[0]["transaction_id"] = rows[1]["transaction_id"]  # duplicate
    rows[2]["date"] = "not-a-date"
    rows[3]["amount"] = "-5"
    rows[4]["type"] = "unknown"
    rows[5]["user_id"] = "22222222-2222-2222-2222-222222222222"
    errors = demo_data.validate_rows(rows)
    assert any("duplicate" in e for e in errors)
    assert any("invalid date" in e for e in errors)
    assert any("positive" in e for e in errors)
    assert any("invalid type" in e for e in errors)
    assert any("inconsistent user_id" in e for e in errors)


def test_committed_csv_valid(tmp_path):
    repo_root = Path(__file__).resolve().parents[4]  # apps/api/tests/unit -> repo root
    csv_path = repo_root / "data" / "demo_data.csv"
    rows = demo_data.load_csv(csv_path)
    errors = demo_data.validate_rows(rows)
    assert errors == [], errors


def test_write_and_reload_roundtrip(tmp_path):
    dest = tmp_path / "out.csv"
    rows = _gen()
    demo_data.write_csv(dest, rows)
    loaded = demo_data.load_csv(dest)
    assert len(loaded) == len(rows)
    assert [r["transaction_id"] for r in loaded] == [r["transaction_id"] for r in rows]