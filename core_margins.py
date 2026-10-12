"""Marja per SKU (SRL platitor TVA vs neplatitor), cantitati importate si stoc estimat."""
import numpy as np
import pandas as pd


def sku_key(s):
    """Cheie de potrivire SKU: fara spatii, majuscule (8821-ds == 8821-DS)."""
    return s.astype(str).str.strip().str.upper()


def weighted_costs(lines_calc, orders_calc, include_status=None):
    """Cost mediu ponderat si cantitati pe SKU. include_status=None -> toate comenzile (inclusiv Draft).
    Intoarce index = cheie SKU; coloane: qty (incluse), qty_excl (excluse), cost_novat, cost_vat."""
    l = lines_calc[lines_calc["valid"]].copy()
    l["_k"] = sku_key(l["sku"])
    inc = l["order_id"].isin(orders_calc["id"] if include_status is None else orders_calc.loc[orders_calc["status"].isin(include_status), "id"])
    g = l[inc].groupby("_k").agg(qty=("qty", "sum"), novat=("total_novat_ron", "sum"), vat=("total_vat_ron", "sum"))
    g["cost_novat"] = g["novat"] / g["qty"]
    g["cost_vat"] = g["vat"] / g["qty"]
    for src, dst in (("price_ron", "c_goods"), ("transport_pc", "c_transport"), ("duty_pc", "c_duty"), ("vat_pc", "c_vat"), ("local_pc", "c_local")):
        g[dst] = (l[inc].assign(_w=l[src] * l["qty"]).groupby("_k")["_w"].sum() / g["qty"])
    g["qty_excl"] = l[~inc].groupby("_k")["qty"].sum().reindex(g.index).fillna(0)
    ex_only = l[~inc].groupby("_k")["qty"].sum().drop(g.index, errors="ignore")
    if len(ex_only):
        g = pd.concat([g, pd.DataFrame({"qty": 0.0, "qty_excl": ex_only})])
    last = l.sort_values("o_date").groupby("_k").last()
    g["buy_price"], g["buy_cur"] = last["unit_price"], last["o_goods_cur"]
    return g[["qty", "qty_excl", "cost_novat", "cost_vat", "c_goods", "c_transport", "c_duty", "c_vat", "c_local", "buy_price", "buy_cur"]]


def margin_table(catalog, costs, min_margin, settings=None):
    """settings: optional (returns_recovery, returns_min_sold, vat_payer)."""
    st_ = settings or {}
    rec, mins = st_.get("returns_recovery", 0.0), st_.get("returns_min_sold", 10)
    c = catalog[catalog["sku"].str.strip() != ""].copy()
    c["_k"] = sku_key(c["sku"])
    c = c.merge(costs, left_on="_k", right_index=True, how="left").drop(columns="_k")
    for col in ("qty", "qty_excl"):
        c[col] = c[col].fillna(0)
    sold, ret = c["sold_qty"].fillna(0), c["returned_qty"].fillna(0)
    c["returns_real"] = ret / sold.replace(0, np.nan)                       # rata REALA = returnat / vandut
    real_ok = c["returns_real"].notna() & (sold >= mins)                     # destule vanzari ca rata reala sa conteze
    c["returns_used"] = np.where(real_ok, c["returns_real"], c["returns_pct"])
    c["returns_source"] = np.where(real_ok, "reala", "estimata")
    c["stock"] = c["qty"] - sold + ret * rec                                # retururile revandabile revin in stoc
    extra = c["packaging"] + c["courier"] + c["storage"] + c["ads"]
    net_price = c["sell_price_vat"] / (1 + c["vat_pct"])
    c["commission_amt"] = c["sell_price_vat"] * c["commission_pct"]
    c["returns_vat"] = c["returns_used"] * (c["cost_novat"] + extra) * (1 - rec)       # cost retur/buc - platitor TVA
    c["returns_nonvat"] = c["returns_used"] * (c["cost_vat"] + extra) * (1 - rec)      # cost retur/buc - neplatitor
    c["sell_costs_vat"] = c["commission_amt"] + extra + c["returns_vat"]
    c["sell_costs_nonvat"] = c["commission_amt"] + extra + c["returns_nonvat"]
    c["profit_vat"] = net_price - c["cost_novat"] - c["sell_costs_vat"]
    c["margin_vat"] = c["profit_vat"] / net_price.replace(0, np.nan)
    c["profit_nonvat"] = c["sell_price_vat"] - c["cost_vat"] - c["sell_costs_nonvat"]
    c["margin_nonvat"] = c["profit_nonvat"] / c["sell_price_vat"].replace(0, np.nan)
    c["diff"] = c["profit_vat"] - c["profit_nonvat"]
    c["better"] = np.where(c["diff"].isna(), "", np.where(c["diff"] > 0, "SRL TVA", "SRL non-TVA"))
    c["below_min"] = np.where(c["margin_vat"].isna() | c["margin_nonvat"].isna(), "",
                              np.where((c["margin_vat"] < min_margin) & (c["margin_nonvat"] < min_margin), "DA - verifica", "OK"))
    m = min_margin   # pret minim pentru marja tinta (cost si retur nu depind de pret => formula inchisa)
    den_n = (1 - c["commission_pct"] - m).where(lambda x: x > 0)
    den_v = ((1 - m) / (1 + c["vat_pct"]) - c["commission_pct"]).where(lambda x: x > 0)
    c["min_price_nonvat"] = (c["cost_vat"] + extra + c["returns_nonvat"]) / den_n
    c["min_price_vat"] = (c["cost_novat"] + extra + c["returns_vat"]) / den_v
    c["min_price"] = np.where(st_.get("vat_payer", False), c["min_price_vat"], c["min_price_nonvat"])
    no_cost = c["cost_novat"].isna()
    c["status"] = np.where(no_cost & (c["qty_excl"] > 0), "Comenzile cu acest SKU sunt excluse (Draft?)",
                   np.where(no_cost, "SKU negasit in nicio comanda (verifica scrierea SKU)",
                   np.where(c["sell_price_vat"].isna() | (c["sell_price_vat"] <= 0), "Completeaza pretul de vanzare cu TVA", "OK")))
    return c


def portfolio(c):
    """Marja medie ponderata cu cantitatea importata (SRL TVA, SRL non-TVA)."""
    c = c.dropna(subset=["profit_vat", "profit_nonvat"])
    c = c[c["qty"] > 0]
    if c.empty:
        return np.nan, np.nan
    mv = (c["profit_vat"] * c["qty"]).sum() / ((c["sell_price_vat"] / (1 + c["vat_pct"])) * c["qty"]).sum()
    mn = (c["profit_nonvat"] * c["qty"]).sum() / (c["sell_price_vat"] * c["qty"]).sum()
    return mv, mn


def catalog_with_order_skus(catalog, lines):
    """Catalogul + SKU-urile din comenzi care nu sunt inca in catalog (cu valori implicite)."""
    import core_schema as schema
    cat = catalog[catalog["sku"].str.strip() != ""]
    ls = lines[lines["sku"].str.strip() != ""]
    new = ls[~sku_key(ls["sku"]).isin(sku_key(cat["sku"]))].drop_duplicates("sku")
    return schema.coerce("catalog", pd.concat([cat, new[["sku", "description", "hs_code"]]], ignore_index=True))
