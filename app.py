import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

# ==========================================
# 1. NASTAVENIA (TU UPRAV SVOJ EMAIL)
# ==========================================
MOJ_EMAIL = "petermarkuska@gmail.com" 
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'

# Konfigurácia stránky
st.set_page_config(page_title="Správa nášho dvora", layout="centered", page_icon="🏡")

# --- FUNKCIA NA NAČÍTANIE DÁT ---
def load_data(sheet_name):
    # Tento link vyexportuje konkrétny hárok z tvojej tabuľky ako CSV
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    return pd.read_csv(url)

# ==========================================
# 2. HLAVNÝ PROGRAM
# ==========================================
try:
    # Načítanie hárkov
    df_p = load_data('Platby')
    df_v = load_data('Vydavky')
    
    # Ošetrenie Variabilných symbolov (aby nezmizli nuly na začiatku)
    df_p['Identifikácia VS'] = df_p['Identifikácia VS'].astype(str).str.zfill(4)

    # VÝPOČTY PRE FINANČNÝ PREHĽAD
    # Hľadáme všetky stĺpce, ktoré končia na /26 (mesiace)
    prijmy_stlpce = [c for c in df_p.columns if '/26' in c]
    celkove_prijmy = pd.to_numeric(df_p[prijmy_stlpce].stack(), errors='coerce').sum()
    celkove_vydavky = pd.to_numeric(df_v['Suma'], errors='coerce').sum()
    zostatok = celkove_prijmy - celkove_vydavky

    # ZOBRAZENIE HLAVIČKY
    st.title("🏡 Portál správy spoločného dvora")
    st.info("Vitajte na stránke pre transparentnú správu našich spoločných financií.")
    
    # METRIKY (TIE TRI OKIENKA HORE)
    c1, c2, c3 = st.columns(3)
    c1.metric("Celkové príjmy", f"{celkove_prijmy:.2f} €")
    c2.metric("Celkové výdavky", f"{celkove_vydavky:.2f} €")
    c3.metric("Aktuálny zostatok", f"{zostatok:.2f} €", delta=None)

    # SEKČIA: MOJA KONTROLA PLATIEB
    st.divider()
    st.subheader("🔎 Moja kontrola platieb")
    moj_vs = st.text_input("Zadajte váš Variabilný symbol (4 číslice, napr. 0101):")

    if moj_vs:
        vysledok = df_p[df_p['Identifikácia VS'] == moj_vs]
        if not vysledok.empty:
            st.success(f"Dáta nájdené pre VS: {moj_vs}")
            # Zobrazenie riadku majiteľa v prehľadnej tabuľke
            st.table(vysledok)
        else:
            st.warning("Zadaný VS sa v databáze nenachádza. Skontrolujte preklepy.")

    # SEKČIA: HLASOVANIE CEZ EMAIL
    st.divider()
    st.subheader("🗳️ Aktuálne hlasovanie")
    tema_hlasovania = "Súhlasíte s investíciou do novej výsadby zelene (odhad 200 €)?"
    st.write(f"**Téma:** {tema_hlasovania}")
    
    if moj_vs:
        # Príprava textov pre email (ošetrenie špeciálnych znakov)
        predmet_ano = urllib.parse.quote(f"HLASOVANIE - ANO - VS {moj_vs}")
        predmet_nie = urllib.parse.quote(f"HLASOVANIE - NIE - VS {moj_vs}")
        telo = urllib.parse.quote(f"Dobrý deň,\n\nodosielam svoj hlas k téme: {tema_hlasovania}\n\nMOJ HLAS: ")

        col_h1, col_h2 = st.columns(2)
        
        with col_h1:
            link_ano = f"mailto:{MOJ_EMAIL}?subject={predmet_ano}&body={telo}ANO"
            st.markdown(f'<a href="{link_ano}" style="text-decoration:none;"><div style="background-color:#28a745; color:white; padding:10px; text-align:center; border-radius:5px; font-weight:bold;">👍 POSLAŤ HLAS: ÁNO</div></a>', unsafe_allow_html=True)
            
        with col_h2:
            link_nie = f"mailto:{MOJ_EMAIL}?subject={predmet_nie}&body={telo}NIE"
            st.markdown(f'<a href="{link_nie}" style="text-decoration:none;"><div style="background-color:#dc3545; color:white; padding:10px; text-align:center; border-radius:5px; font-weight:bold;">👎 POSLAŤ HLAS: NIE</div></a>', unsafe_allow_html=True)
            
        st.caption("Po kliknutí sa vám otvorí e-mailová aplikácia. Hlas odošlite bez zmien.")
    else:
        st.warning("⚠️ Pre odomknutie hlasovacích tlačidiel zadajte svoj VS v sekcii vyššie.")

    # SEKČIA: ZOZNAM VÝDAVKOV
    st.divider()
    st.subheader("📜 Detailný zoznam výdavkov")
    # Zobrazenie tabuľky výdavkov zoradenej od najnovších
    if not df_v.empty:
        st.dataframe(df_v, use_container_width=True, hide_index=True)
    else:
        st.write("Zatiaľ neboli zaevidované žiadne výdavky.")

except Exception as e:
    st.error("Pri načítaní dát nastala chyba.")
    st.write(f"Technický detail: {e}")
    st.info("Skontrolujte, či sú v Google Tabuľke hárky 'Platby' a 'Vydavky' správne pomenované.")
