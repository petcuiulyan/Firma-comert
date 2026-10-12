"""Pagina de start: ghid pas cu pas, situatia pe scurt si sfaturi in limbaj simplu."""
import plotly.express as px
import streamlit as st

import core_advisor as adv
import core_margins as margins
import view_common as c


def render():
    st.title("👋 Bun venit")
    d, s, oc, lc = c.compute_all()
    base = margins.catalog_with_order_skus(d["catalog"], d["lines"])
    mt = margins.margin_table(base, margins.weighted_costs(lc, oc), s["min_margin"], s)
    steps = adv.checklist(d, s, oc, mt, d["months"])
    done = sum(1 for x in steps if x[0])
    st.markdown("Aici vezi **unde ești** și **ce ai de făcut în continuare**. Parcurge pașii de sus în jos; aplicația îi bifează singură.")
    st.progress(done / len(steps), text=f"{done} din {len(steps)} pași făcuți")
    nxt = next((x for x in steps if not x[0]), None)
    if nxt:
        st.success(f"**Următorul pas:** {nxt[1]}  \n{nxt[2]}", icon="👉")
        c.goto(nxt[3], "➡️ Mergi la pasul acesta")
    else:
        st.success("Ai parcurs toți pașii de bază. De acum, repetă lunar: comandă → costuri → vânzări → închide luna.", icon="🎉")
    with st.expander("Lista completă de pași", expanded=not done):
        for ok, title, hint, page in steps:
            st.markdown(f"{'✅' if ok else '⬜'} **{title}** – {hint}")

    st.subheader("Pe scurt")
    mv, mn = margins.portfolio(mt)
    mine = mv if s["vat_payer"] else mn
    k = st.columns(4)
    k[0].metric("Comenzi făcute", len(oc))
    k[1].metric("Bucăți aduse", f"{mt['qty'].sum():,.0f}" if len(mt) else "0")
    k[2].metric("Câștigi la 100 lei vânduți", "–" if mine != mine else f"{mine * 100:.0f} lei", help="Marja medie, după toate costurile.")
    k[3].metric("Stoc estimat (buc)", f"{mt['stock'].sum():,.0f}" if len(mt) else "0")

    tips = adv.insights(d, s, oc, mt, d["months"])
    if tips:
        st.subheader("Ce merită atenția ta")
        for lvl, txt in tips:
            {"warn": st.warning, "info": st.info, "ok": st.success}[lvl](txt)
    cs = adv.cost_structure(lc)
    if sum(cs.values()) > 0:
        st.subheader("Din ce e făcut costul mărfii aduse")
        tot = sum(cs.values())
        a, b = st.columns([2, 3])
        a.plotly_chart(px.pie(names=list(cs), values=list(cs.values()), hole=0.5), width="stretch")
        b.markdown("\n".join(f"- **{k}**: {v:,.0f} lei ({v / tot:.0%})" for k, v in cs.items() if v > 0))
        b.caption("Dacă transportul sau taxele sunt o parte mare, merită să cauți oferte mai bune sau să comanzi în cantități mai mari.")
    with st.expander("📖 Glosar: termenii pe înțelesul tuturor"):
        for term, expl in adv.GLOSSARY.items():
            st.markdown(f"**{term}** – {expl}")
