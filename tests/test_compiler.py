"""End-to-end compiler tests (plan Step 1.8)."""
import shutil
import sqlite3
from pathlib import Path

import pytest

from forge.compiler import compile_platform
from forge.compiler.parser import load_spec

SPEC_PATH = Path("specs/aureon.platform.yaml")
OUTPUT_DIR = Path("test_output/aureon")


@pytest.fixture(autouse=True)
def clean_output():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    yield
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)


def test_spec_loads():
    spec = load_spec(SPEC_PATH)
    assert spec.platform.name == "aureon"
    assert len(spec.entities) == 3


def test_compile_produces_files():
    spec = load_spec(SPEC_PATH)
    result = compile_platform(spec, OUTPUT_DIR)
    assert len(result.files_generated) >= 8
    assert (OUTPUT_DIR / "app.py").exists()
    assert (OUTPUT_DIR / "models" / "__init__.py").exists()
    assert (OUTPUT_DIR / "routes" / "__init__.py").exists()
    assert (OUTPUT_DIR / "migrations" / "001_initial_sqlite.sql").exists()


def test_generated_sql_executes():
    spec = load_spec(SPEC_PATH)
    compile_platform(spec, OUTPUT_DIR)
    sql = (OUTPUT_DIR / "migrations" / "001_initial_sqlite.sql").read_text()
    conn = sqlite3.connect(":memory:")
    conn.executescript(sql)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    assert "opportunity" in tables
    assert "vendor" in tables
    conn.close()


def test_generated_app_is_valid_python():
    spec = load_spec(SPEC_PATH)
    compile_platform(spec, OUTPUT_DIR)
    app_code = (OUTPUT_DIR / "app.py").read_text()
    compile(app_code, str(OUTPUT_DIR / "app.py"), "exec")
