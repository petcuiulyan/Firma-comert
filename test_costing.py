"""Verificare fata de valorile calculate de Excel (Calculator_Cost_Import_Mostre_refacut.xlsx)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import costing, storage
from core.settings import DEFAULTS

XLSX = Path(__file__).parent / "fixtures" / "Calculator_Cost_Import_Mostre_refacut.xlsx"


@pytest.mark.skipif(not XLSX.exists(), reason="fisierul de referinta lipseste")
def test_matches_excel():
    o, l = storage.import_legacy_excel(XLSX)
    s = {**DEFAULTS, "vat_std": 0.21}
    oc, lc = costing.compute(o, l, s)
    xl = pd.read_excel(XLSX, sheet_name="Calculator Cost per Bucata", header=None, skiprows=9, usecols="A:W", nrows=7)
    xl.columns = list("ABCDEFGHIJKLMNOPQRSTUVW")
    lc = lc.sort_values("sku", key=lambda x: x.astype(str)).reset_index(drop=True)
    xl["C"] = xl["C"].astype(str)
    xl = xl.sort_values("C").reset_index(drop=True)
    for col, mine in [("P", "cost_novat_ron"), ("S", "cost_vat_ron"), ("Q", "cost_novat_eur"), ("U", "cost_vat_usd"), ("W", "total_vat_ron")]:
        assert np.allclose(xl[col].astype(float).values, lc[mine].values, atol=0.01), col
