"""Marja per produs: preturi (RON), vanzari si retururi, rata de retur REALA, pret minim, simulator."""
import pandas as pd
import streamlit as st

import core_costing as costing
import core_margins as margins
import core_schema as schema
import core_storage as storage
import view_common as c

PCT = ["vat_pct", "commission_pct", "returns_pct"]


def render():
    st.title("📈 Marjă, retururi și stoc")
    c.intro("Cât câștigi pe fiecare produs după toate costurile. Completezi prețul de vânzare (în RON) și ce ai vândut / ți s-a returnat; aplicația calculează profitul, "
            "rata de retur reală și **prețul minim** la care mai ieși pe marja dorită.")
    d, s, oc, lc = c.compute_all()
    inc_draft = st.toggle("Include comenzile Draft (neplasate) în cost și cantități", value=True,
                          help="Comenzile noi sunt 'Draft' până le schimbi statusul în pagina Comenzi.")
    statuses = None if inc_draft else [x for x in schema.STATUSES if x != "Draft"]
    base = margins.catalog_with_order_skus(d["catalog"], d["lines"])
    if base.empty:
        c.info_empty("Nu există produse. Încarcă un PI în **Produse & PI** sau creează o comandă."); return
    st.info("💱 **Monede:** achiziția se face în **USD/EUR** (cum e pe PI) și se convertește în RON la cursul fiecărei comenzi. "
            "**Vânzarea (eMAG / site) este în RON.** Toate costurile, prețurile și marjele de pe pagină sunt în **RON**.")

    st.subheader("1 · Prețuri și costuri de vânzare (RON per bucată)")
    e1 = base[["sku", "description", "sell_price_vat", "vat_pct", "commission_pct", "returns_pct", "packaging", "storage", "courier", "ads"]].copy()
    e1[PCT] = e1[PCT] * 100
    n = lambda t, h=None: st.column_config.NumberColumn(t, format="%.2f", help=h)
    ed1 = st.data_editor(e1, hide_index=True, width="stretch", key="mg1", disabled=["sku", "description"], column_config={
        "sku": "SKU", "description": "Descriere", "sell_price_vat": n("Preț vânzare cu TVA (RON)", "Prețul la care vinzi clientului, cu TVA inclus."),
        "vat_pct": n("TVA vânzare (%)", "21 = 21%"), "commission_pct": n("Comision marketplace (%)", "eMAG ~15%; 0 pentru site propriu."),
        "returns_pct": n("Retur estimat (%)", "Folosit până ai destule vânzări ca să se calculeze rata reală."),
        "packaging": n("Ambalare/buc"), "storage": n("Depozitare/buc"), "courier": n("Livrare/buc"), "ads": n("Reclame/buc")})
    st.subheader("2 · Vânzări și retururi (le actualizezi periodic, cumulat)")
    ed2 = st.data_editor(base[["sku", "description", "sold_qty", "returned_qty"]], hide_index=True, width="stretch", key="mg2", disabled=["sku", "description"],
                         column_config={"sku": "SKU", "description": "Descriere", "sold_qty": st.column_config.NumberColumn("Vândut (buc, total)", format="%.0f"),
                                        "returned_qty": st.column_config.NumberColumn("Returnat (buc, total)", format="%.0f", help="Rata de retur = returnat ÷ vândut, calculată automat.")})
    live = base.copy()
    for col in ("sell_price_vat", "vat_pct", "commission_pct", "returns_pct", "packaging", "storage", "courier", "ads"):
        live[col] = ed1[col].values / (100 if col in PCT else 1)
    live["sold_qty"], live["returned_qty"] = ed2["sold_qty"].values, ed2["returned_qty"].values
    if st.button("💾 Salvează", type="primary"):
        storage.save("catalog", live); st.toast("Salvat în catalog.", icon="✅"); st.rerun()

    costs = margins.weighted_costs(lc, oc, statuses)
    mt = margins.margin_table(live, costs, s["min_margin"], s)
    mv, mn = margins.portfolio(mt)
    mine = mv if s["vat_payer"] else mn
    real = mt[mt["returns_source"] == "reala"]
    st.subheader("3 · Rezultat")
    k = st.columns(4)
    k[0].metric("Bucăți importate", f"{mt['qty'].sum():,.0f}"); k[1].metric("Stoc estimat", f"{mt['stock'].sum():,.0f}")
    k[2].metric("Marjă medie (regimul tău)", "–" if mine != mine else f"{mine:.1%}", help="Din 100 lei încasați, atâția rămân profit.")
    k[3].metric("Rată retur reală medie", "–" if real.empty else f"{real['returns_used'].mean():.1%}")
    cost_col, prof_col, marg_col = ("cost_novat", "profit_vat", "margin_vat") if s["vat_payer"] else ("cost_vat", "profit_nonvat", "margin_nonvat")
    d_ = mt.copy()
    d_["buy"] = [f"{p:,.2f} {cu}" if p == p else "–" for p, cu in zip(d_["buy_price"], d_["buy_cur"].fillna(""))]
    pc = lambda t, h=None: st.column_config.NumberColumn(t, format="percent", help=h)
    st.dataframe(d_[["sku", "description", "status", "buy", cost_col, "sell_price_vat", prof_col, marg_col, "min_price", "returns_used", "returns_source", "stock"]],
                 hide_index=True, width="stretch", column_config={
                     "sku": "SKU", "description": "Descriere", "status": "Stare calcul", "buy": "Achiziție (moneda facturii)",
                     cost_col: n("Cost real/buc (RON)", "Tot ce te costă o bucată în depozit" + (", fără TVA import." if s["vat_payer"] else ", cu TVA import.")),
                     "sell_price_vat": n("Vânzare cu TVA (RON)"), prof_col: n("Profit/buc (RON)"), marg_col: pc("Marjă"),
                     "min_price": n(f"Preț minim pt. marjă {s['min_margin']:.0%}", "Sub acest preț (cu TVA) marja scade sub ținta din Setări."),
                     "returns_used": pc("Rată retur folosită"), "returns_source": "Retur: sursă", "stock": st.column_config.NumberColumn("Stoc estimat", format="%.0f")})
    st.caption(f"Regim: **{'plătitor' if s['vat_payer'] else 'neplătitor'} de TVA** (se schimbă în Setări). Rata de retur „reală” = returnat ÷ vândut, după cel puțin "
               f"{int(s['returns_min_sold'])} bucăți vândute; până atunci se folosește estimarea. Cost retur = rată × (cost + costuri de vânzare), cu {s['returns_recovery']:.0%} din produse revândute.")

    with st.expander("🧪 Simulator: ce se întâmplă dacă…"):
        a = st.columns(3)
        fx = a[0].slider("Cursul USD/EUR se schimbă cu (%)", -20, 20, 0)
        buy = a[1].slider("Furnizorul schimbă prețul cu (%)", -20, 20, 0)
        sell = a[2].slider("Schimb prețul de vânzare cu (%)", -20, 20, 0)
        o2, l2, live2 = d["orders"].copy(), d["lines"].copy(), live.copy()
        o2["usd_ron"] *= 1 + fx / 100; o2["eur_ron"] *= 1 + fx / 100; l2["unit_price"] *= 1 + buy / 100; live2["sell_price_vat"] *= 1 + sell / 100
        oc2, lc2 = costing.compute(o2, l2, s)
        mt2 = margins.margin_table(live2, margins.weighted_costs(lc2, oc2, statuses), s["min_margin"], s)
        mv2, mn2 = margins.portfolio(mt2)
        m2 = mv2 if s["vat_payer"] else mn2
        b = st.columns(2)
        b[0].metric("Marjă medie acum", "–" if mine != mine else f"{mine:.1%}")
        b[1].metric("Marjă medie în scenariu", "–" if m2 != m2 else f"{m2:.1%}", None if (mine != mine or m2 != m2) else f"{(m2 - mine) * 100:+.1f} puncte")
        cmp_ = pd.DataFrame({"SKU": mt["sku"], "Marjă acum": mt[marg_col], "Marjă scenariu": mt2[marg_col]})
        st.dataframe(cmp_, hide_index=True, width="stretch", column_config={"Marjă acum": pc("Marjă acum"), "Marjă scenariu": pc("Marjă în scenariu")})
    with st.expander("🔎 Din ce e făcut costul unei bucăți (RON)"):
        b = mt[["sku", "c_goods", "c_transport", "c_duty", "c_vat", "c_local", "packaging", "storage", "courier", "ads", "commission_amt", "returns_nonvat",
                "cost_vat", "sell_costs_nonvat", "sell_price_vat", "profit_nonvat"]].copy()
        b["total"] = b["cost_vat"] + b["sell_costs_nonvat"]
        st.dataframe(b.drop(columns=["cost_vat", "sell_costs_nonvat"]), hide_index=True, width="stretch", column_config={
            "sku": "SKU", "c_goods": n("Achiziție"), "c_transport": n("Transport"), "c_duty": n("Taxă vamală"), "c_vat": n("TVA import"), "c_local": n("Broker/local"),
            "packaging": n("Ambalare"), "storage": n("Depozitare"), "courier": n("Livrare"), "ads": n("Reclame"), "commission_amt": n("Comision"),
            "returns_nonvat": n("Retur"), "total": n("TOTAL costuri"), "sell_price_vat": n("Preț vânzare"), "profit_nonvat": n("PROFIT/buc")})
        st.caption("Varianta neplătitor de TVA. Pentru plătitor: scazi „TVA import” din total și împarți prețul de vânzare la (1 + TVA).")
