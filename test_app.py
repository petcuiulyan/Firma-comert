"""Test de fum: fiecare pagina porneste fara exceptii, pe date importate din Excel."""
import os, sys, tempfile
from pathlib import Path
import pytest
os.environ["IMPORT_APP_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from streamlit.testing.v1 import AppTest
from core import storage

FX = Path(__file__).parent / "fixtures" / "Calculator_Cost_Import_Mostre_refacut.xlsx"
PAGES = ["dashboard", "catalog_pi", "new_order", "orders", "cost", "transport", "margins", "fiscal", "settings"]


@pytest.mark.parametrize("page", PAGES)
def test_page_runs(page):
    if FX.exists():
        o, l = storage.import_legacy_excel(FX); storage.save("orders", o); storage.save("lines", l)
    at = AppTest.from_string(f"from views import {page}\n{page}.render()", default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
