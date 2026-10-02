"""Runs the SQL schema, seed data, views, star schema and ETL against a real PostgreSQL database and
checks the KPI results.

Skipped unless EAM_DATABASE_URL points at a disposable database: its `public` and `dw` schemas are
dropped and recreated."""

import os
import re
from decimal import Decimal
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

URL = os.environ.get("EAM_DATABASE_URL")
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
pytestmark = pytest.mark.skipif(not URL, reason="EAM_DATABASE_URL not set")


@pytest.fixture(scope="module")
def conn():
    with psycopg.connect(URL, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS dw CASCADE")
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        for f in sorted(SQL_DIR.glob("0[1-5]_*.sql")):
            c.execute(f.read_text())
        yield c


def named_queries() -> dict[str, str]:
    text = (SQL_DIR / "06_analytics_queries.sql").read_text()
    parts = re.split(r"^-- name: (\w+)\n", text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].split(";")[0] for i in range(1, len(parts), 2)}


def test_reliability_function(conn):
    rows = conn.execute(
        "SELECT asset_num, failures, downtime_hours, mttr_hours"
        " FROM asset_reliability('2026-01-01', '2026-10-01') WHERE asset_num = 'P101'"
    ).fetchall()
    assert rows == [("P101", 3, Decimal("14.50"), Decimal("4.83"))]


def test_cost_rollup_uses_the_hierarchy(conn):
    rows = dict(
        conn.execute("SELECT asset_num, labor_cost + material_cost FROM v_asset_cost_rollup").fetchall()
    )
    assert rows["P101"] == Decimal("1240.00")
    assert rows["AHU1"] == Decimal("140.00")


def test_pm_compliance_and_backlog(conn):
    compliance = conn.execute(
        "SELECT month::text, compliance FROM v_pm_compliance_monthly ORDER BY 1"
    ).fetchall()
    assert compliance == [
        ("2026-04-01", Decimal("1.00")),
        ("2026-07-01", Decimal("0.00")),
        ("2026-08-01", Decimal("1.00")),
    ]
    assert conn.execute("SELECT open_work_orders FROM v_backlog").fetchone() == (2,)
    reorder = {r[0] for r in conn.execute("SELECT item_num FROM v_reorder_required").fetchall()}
    assert reorder == {"SEAL-KIT-40", "FLT-AHU"}


def test_pm_generation_is_idempotent_per_occurrence(conn):
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(
            "INSERT INTO work_orders (wo_num, site_id, asset_id, work_type, status, priority, description,"
            " pm_id, target_start) VALUES ('WO-DUP', 1, 1, 'PM', 'APPROVED', 3, 'dup', 1, '2026-04-05')"
        )


def test_corrective_work_cannot_close_without_failure_codes(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO work_orders (wo_num, site_id, asset_id, work_type, status, priority, description)"
            " VALUES ('WO-BAD', 1, 1, 'CM', 'CLOSED', 2, 'no codes')"
        )


def test_star_schema_analytics(conn):
    q = named_queries()
    assert set(q) == {
        "cost_by_class_and_work_type",
        "planned_maintenance_percentage",
        "top_failure_modes",
        "mttr_by_criticality",
    }
    assert conn.execute(q["planned_maintenance_percentage"]).fetchone() == (Decimal("0.1875"),)
    top = conn.execute(q["top_failure_modes"]).fetchall()
    assert top[0][:3] == ("LEAK", "SEAL-WEAR", 2)
    assert conn.execute(q["mttr_by_criticality"]).fetchall() == [("A", Decimal("4.83"), 3)]
