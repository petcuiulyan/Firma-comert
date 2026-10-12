"""Sfaturi in limbaj simplu: pasi de urmat, avertismente utile, structura costului, glosar."""
import numpy as np
import pandas as pd

import core_storage as storage

GLOSSARY = {
    "PI (Proforma Invoice)": "Oferta/factura proforma de la furnizor: ce produse, cate bucati, la ce pret.",
    "Valoare in vama (CIF)": "Pretul marfii + transportul pana la granita UE. Pe ea se calculeaza taxele vamale.",
    "Taxa vamala": "Taxa platita la intrarea marfii in UE, un procent din valoarea in vama (depinde de codul NC al produsului).",
    "TVA import": "TVA platit la vama. Daca firma e platitoare de TVA il recuperezi; daca nu, devine cost real.",
    "Cost per bucata": "Cat te costa o bucata pusa in depozitul tau: marfa + transport + taxe + TVA (daca nu il recuperezi) + costuri locale.",
    "Marja": "Din 100 lei incasati, cati raman profit dupa toate costurile. Marja 30% = 30 lei profit la 100 lei.",
    "Pret minim de vanzare": "Cel mai mic pret cu care mai iesi pe marja tinta (setata in Setari).",
    "Rata de retur": "Din 100 bucati vandute, cate se intorc. Se calculeaza singura: returnat ÷ vandut.",
    "OPEX": "Cheltuieli lunare de functionare (contabil, depozit, reclame, abonamente), indiferent cat vinzi.",
    "Cash vs contabil": "Cash = ce iese din buzunar luna asta (inclusiv stocul cumparat). Contabil = doar costul marfii efectiv vandute.",
    "Plafon TVA": "Daca incasarile depasesc plafonul, devii obligat sa te inregistrezi ca platitor de TVA.",
    "Draft": "Comanda pregatita, dar inca neplasata la furnizor.",
}


def checklist(d, s, oc, mt, months):
    """Pasii de baza pentru un incepator, bifati automat din datele existente."""
    has_orders = len(oc) > 0
    priced = mt["sell_price_vat"].gt(0).sum() if len(mt) else 0
    return [
        (( storage.DATA_DIR / "settings.json").exists(), "Verifică setările firmei", "Alege dacă ești plătitor de TVA și verifică cursurile și taxele.", "settings"),
        (len(d["catalog"]) > 0 or len(d["lines"]) > 0, "Adaugă produsele (încarcă un PI)", "Încarci oferta furnizorului; produsele ajung în catalog.", "catalog_pi"),
        (has_orders and bool((oc["transp_rate"] > 0).any()), "Creează o comandă și completează transportul și cursul", "Fără transport și curs, costul real nu se poate calcula.", "orders"),
        (bool(len(mt) and mt["cost_novat"].notna().any()), "Verifică cât te costă fiecare bucată", "Costul real, în RON, EUR și USD.", "cost"),
        (len(mt) > 0 and priced == len(mt), "Pune prețul de vânzare (în RON) la fiecare produs", "Fără preț de vânzare nu se poate calcula profitul.", "margins"),
        (has_orders and bool((oc["status"] != "Draft").any()), "Marchează comanda ca plasată / recepționată", "Schimbi statusul din Draft în pagina Comenzi.", "orders"),
        (bool(len(mt) and mt["sold_qty"].fillna(0).sum() > 0), "Notează ce ai vândut și ce s-a returnat", "Din ele se calculează stocul, rata de retur și veniturile.", "margins"),
        (bool((months["closed"] == "Da").any()) if len(months) else False, "Închide prima lună", "Aplicația adună costurile, vânzările și OPEX-ul lunii.", "fiscal"),
    ]


def cost_structure(lc):
    """Din ce e facut costul total: marfa, transport, taxe vamale, TVA import, costuri locale."""
    v = lc[lc["valid"]]
    parts = {"Marfă": (v["price_ron"] * v["qty"]).sum(), "Transport": (v["transport_pc"] * v["qty"]).sum(), "Taxe vamale": (v["duty_pc"] * v["qty"]).sum(),
             "TVA import": (v["vat_pc"] * v["qty"]).sum(), "Costuri locale": (v["local_pc"] * v["qty"]).sum()}
    return {k: float(x) for k, x in parts.items()}


def insights(d, s, oc, mt, months, today=None):
    """Lista de (nivel, text): warn / info / ok. Doar lucruri care chiar conteaza."""
    out = []
    today = today or pd.Timestamp.today()
    nd = int((oc["status"] == "Draft").sum()) if len(oc) else 0
    if nd:
        out.append(("info", f"{nd} comenzi sunt încă **Draft** (neplasate). Costurile lor sunt incluse ca estimare."))
    if len(mt):
        nop = mt[mt["sell_price_vat"].isna() | (mt["sell_price_vat"] <= 0)]
        if len(nop):
            out.append(("info", f"{len(nop)} produse nu au **preț de vânzare**: fără el nu pot calcula profitul ({', '.join(nop['sku'].head(4))}...)."))
        low = mt[(mt["margin_vat"].notna()) & (mt["margin_nonvat"].notna()) & (mt["margin_nonvat" if not s["vat_payer"] else "margin_vat"] < s["min_margin"])]
        if len(low):
            ex = low.iloc[0]
            out.append(("warn", f"{len(low)} produse au marja sub {s['min_margin']:.0%}. Ex.: **{ex['sku']}** – ar trebui vândut cu cel puțin **{ex['min_price']:.0f} lei** (cu TVA)."))
        hi = mt[(mt["returns_source"] == "reala") & (mt["returns_used"] > 0.10)]
        if len(hi):
            out.append(("warn", f"Rată de retur mare (peste 10%) la: {', '.join(hi['sku'].head(4))}. Verifică calitatea produsului sau descrierea din anunț."))
        sold_out = mt[(mt["qty"] > 0) & (mt["stock"] <= 0)]
        if len(sold_out):
            out.append(("warn", f"Stoc epuizat la: {', '.join(sold_out['sku'].head(5))}. Dacă se vând bine, comandă din timp (transportul durează)."))
    if len(oc) >= 2:
        t = oc.dropna(subset=["date", "ron_per_kg"]).sort_values("date")
        if len(t) >= 2 and t.iloc[-2]["ron_per_kg"] > 0:
            ch = t.iloc[-1]["ron_per_kg"] / t.iloc[-2]["ron_per_kg"] - 1
            if abs(ch) > 0.15:
                out.append(("warn" if ch > 0 else "info", f"Transportul a {'crescut' if ch > 0 else 'scăzut'} cu **{abs(ch):.0%}** (RON/kg) față de comanda anterioară. Compară ofertele."))
    if len(oc):
        last = oc.dropna(subset=["date"]).sort_values("date").iloc[-1] if oc["date"].notna().any() else None
        if last is not None and last["usd_ron"] > 0 and abs(s["usd_ron"] / last["usd_ron"] - 1) > 0.03:
            out.append(("info", f"Cursul USD din Setări ({s['usd_ron']:.2f}) diferă cu {abs(s['usd_ron'] / last['usd_ron'] - 1):.0%} de cel din ultima comandă: costurile viitoare vor fi diferite."))
    if len(months):
        cl = months[months["closed"] == "Da"]
        if len(cl):
            ca = cl["revenue_vat"].sum() / len(cl) * 12
            pct = ca / s["vat_threshold"] if s["vat_threshold"] else 0
            out.append(("warn" if pct > 0.8 else "ok", f"La ritmul actual vei încasa ~**{ca:,.0f} lei/an** = **{pct:.0%}** din plafonul de TVA ({s['vat_threshold']:,.0f} lei)."))
    if len(oc) and oc["date"].notna().any():
        old_open = [m for m in sorted(set(oc["date"].dropna().dt.strftime("%Y-%m"))) if m < today.strftime("%Y-%m") and (not len(months) or m not in set(months.loc[months["closed"] == "Da", "month"]))]
        if old_open:
            out.append(("info", f"Luna **{old_open[0]}** nu e încă închisă (pagina Fiscal)."))
    return out
