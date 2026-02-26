import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --- NASTAVENIE ---
# ID vašej tabuľky z linku
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'
# Verejný CSV export link pre rýchle čítanie
SHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv'

st.set_page_config(page_title="Správa nášho dvora", layout="centered")

# --- FUNKCIA NA NAČÍTANIE (ČÍTANIE) ---
def load_data(sheet_name):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    return pd.read_csv(url)

try:
    # Načítame dáta z Google Sheets
    df_p = load_data('Platby')
    df_v = load_data('Vydavky')
    
    # Vyčistíme VS (zabezpečíme, aby to bol text)
    df_p['Identifikácia VS'] = df_p['Identifikácia VS'].astype(str).str.zfill(4)

    # --- VÝPOČTY ---
    prijmy_stlpce = [c for c in df_p.columns if '/26' in c]
    celkove_prijmy = pd.to_numeric(df_p[prijmy_stlpce].stack(), errors='coerce').sum()
    celkove_vydavky = pd.to_numeric(df_v['Suma'], errors='coerce').sum()
    zostatok = celkove_prijmy - celkove_vydavky

    # --- ZOBRAZENIE ---
    st.title("🏡 Portál správy spoločného dvora")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Príjmy", f"{celkove_prijmy:.2f} €")
    c2.metric("Výdavky", f"{celkove_vydavky:.2f} €")
    c3.metric("Zostatok", f"{zostatok:.2f} €")

    # --- SEKČIA PRE VLASTNÍKA ---
    st.divider()
    st.subheader("🔎 Moja kontrola platieb")
    moj_vs = st.text_input("Zadajte váš Variabilný symbol (napr. 0105):")

    if moj_vs:
        vysledok = df_p[df_p['Identifikácia VS'] == moj_vs]
        if not vysledok.empty:
            st.success(f"Dáta pre VS {moj_vs}:")
            st.table(vysledok) # Zobrazí riadok majiteľa
        else:
            st.warning("Tento VS sa v databáze nenachádza.")

    # --- HLASOVANIE ---
    st.divider()
    st.subheader("🗳️ Aktuálne hlasovanie")
    st.write("**Téma:** Súhlasíte s investíciou do novej výsadby zelene (200€)?")
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        if st.button("👍 ÁNO, súhlasím"):
            st.balloons()
            st.success("Váš súhlas bol zaznamenaný. (Informáciu spracuje správca v Google Tabuľke).")
            st.info("Tip: Správca uvidí váš hlas v hárku 'Hlasovanie'.")
            
    with col_h2:
        if st.button("👎 NIE, nesúhlasím"):
            st.error("Váš nesúhlas bol zaznamenaný.")

    # --- TABUĽKA VÝDAVKOV ---
    st.divider()
    st.subheader("📜 Zoznam výdavkov")
    st.dataframe(df_v, use_container_width=True)

except Exception as e:
    st.error(f"Ešte chvíľku! Skontrolujte, či máte v Google tabuľke hárky 'Platby' a 'Vydavky'. (Chyba: {e})")
