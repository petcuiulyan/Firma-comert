"""Import Calculator – punct de intrare Streamlit. Fiecare sectiune e in views/<nume>.py, iar calculele in core/<nume>.py."""
import streamlit as st

import core_storage as storage
import view_assistant as assistant
import view_catalog_pi as catalog_pi
import view_common as common
import view_cost as cost
import view_dashboard as dashboard
import view_fiscal as fiscal
import view_home as home
import view_margins as margins
import view_new_order as new_order
import view_orders as orders
import view_settings as settings
import view_transport as transport

st.set_page_config(page_title="Import Calculator", page_icon="📦", layout="wide")

P = {
    "home": st.Page(home.render, title="Start / Ghid", icon="👋", url_path="start", default=True),
    "catalog_pi": st.Page(catalog_pi.render, title="Produse & PI", icon="📦", url_path="produse"),
    "new_order": st.Page(new_order.render, title="Comandă nouă", icon="🛒", url_path="comanda-noua"),
    "orders": st.Page(orders.render, title="Comenzi", icon="🧾", url_path="comenzi"),
    "cost": st.Page(cost.render, title="Cost per bucată", icon="💶", url_path="cost"),
    "transport": st.Page(transport.render, title="Capacitate transport", icon="🚚", url_path="transport"),
    "margins": st.Page(margins.render, title="Marjă, retururi, stoc", icon="📈", url_path="marja"),
    "dashboard": st.Page(dashboard.render, title="Grafice", icon="📊", url_path="grafice"),
    "fiscal": st.Page(fiscal.render, title="Fiscal și închidere lună", icon="🏛️", url_path="fiscal"),
    "settings": st.Page(settings.render, title="Setări & Backup", icon="⚙️", url_path="setari"),
    "assistant": st.Page(assistant.render, title="Asistent AI", icon="🤖", url_path="asistent"),
}
common.PAGES = P
pages = {
    "Început": [P["home"]],
    "1 · Aprovizionare": [P["catalog_pi"], P["new_order"], P["orders"], P["cost"], P["transport"]],
    "2 · Vânzare și profit": [P["margins"], P["dashboard"]],
    "3 · Firmă și taxe": [P["fiscal"]],
    "Sistem": [P["settings"], P["assistant"]],
}
with st.sidebar:
    _s = storage.load_settings()
    st.caption(f"Regim: **{'plătitor' if _s['vat_payer'] else 'neplătitor'} de TVA**")
    st.download_button("⬇️ Descarcă backup date", storage.export_backup(), "backup_import_calculator.xlsx",
                       help="Pe Streamlit Cloud datele se pierd la repornire – descarcă un backup după fiecare sesiune importantă.")
st.navigation(pages).run()
