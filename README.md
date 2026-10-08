# Import Calculator

Aplicație Streamlit pentru importul de marfă din China: cost real per bucată (RON/EUR/USD), comenzi cu curs și transport propriu,
încărcare PI de la furnizori, capacitate de transport, marjă per produs și comparație fiscală.

## Pornire locală
```bash
pip install -r requirements.txt
streamlit run app.py
```
Datele se salvează în `data/` (ignorat de git). Prima dată: **Setări & Backup → Importă din calculatorul Excel**.

## Structură (cod pe secțiuni)
| Pagina (`views/`) | Calculele ei (`core/`) | Ce face |
|---|---|---|
| `dashboard.py` | – | KPI-uri și grafice |
| `catalog_pi.py` | `pi_parser.py`, `catalog.py` | Încarcă PI, compară cu catalogul, actualizează/adaugă produse, creează comandă |
| `new_order.py` | `costing.py`, `capacity.py` | Comandă nouă: produse din catalog, cartoane/paleți, estimare cost |
| `orders.py` | `costing.py` | Editare comenzi (dată, curs, transport) |
| `cost.py` | `costing.py` | Cost per bucată în 3 monede + comparație piață RO |
| `transport.py` | `capacity.py` | Cartoane → paleți → camion/container/avion |
| `margins.py` | `margins.py` | Marjă SRL TVA vs non-TVA |
| `fiscal.py` | `fiscal.py` | P&L, OPEX, 4 regimuri × 5 scenarii |
| `settings.py` | `storage.py`, `settings.py` | Setări, taxe pe cod NC, backup, import Excel |

`core/schema.py` definește tabelele (o singură sursă de adevăr), `core/storage.py` persistența.

## Teste
```bash
pytest
```
`tests/test_costing.py` compară rezultatele cu valorile calculate de Excel; `tests/test_app.py` pornește fiecare pagină.
Fișierul din `tests/fixtures/` conține date reale – șterge-l dacă repo-ul nu e privat (testul se sare singur).

## Deploy pe Streamlit Community Cloud
Repo **privat**, `app.py` ca fișier principal. Atenție: stocarea locală e **temporară** la repornire – folosește
**Setări & Backup → Descarcă backup** periodic și restaurează după redeploy.
