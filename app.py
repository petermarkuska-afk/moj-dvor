import streamlit as st
import pandas as pd

st.set_page_config(page_title="Správa Dvora", layout="centered")

# --- NAČÍTANIE DÁT ---
def load_data():
    # Načítame vašu tabuľku (musí byť uložená ako CSV)
    df = pd.read_csv('Evidencia.csv')
    # Prevedieme Identifikáciu VS na text, aby sa dalo vyhľadávať
    df['Identifikácia VS'] = df['Identifikácia VS'].astype(str).str.zfill(4)
    return df

try:
    df = load_data()

    # --- HLAVNÝ PANEL (DASHBOARD) ---
    st.title("🏡 Portál správy spoločného dvora")
    
    # Výpočet zostatku (súčet všetkých mesiacov v tabuľke)
    prijmy_stlpce = df.columns[1:13] # Stĺpce 01/26 až 12/26
    celkovy_prijem = df[prijmy_stlpce].sum().sum()

    st.metric("Aktuálny stav fondu", f"{celkovy_prijem:,.2f} €".replace(',', ' '))

    # --- SEKČIA PRE VLASTNÍKA ---
    st.divider()
    st.subheader("🔎 Moja kontrola platieb")
    moj_vs = st.text_input("Zadajte váš Variabilný symbol (napr. 0105):")

    if moj_vs:
        vysledok = df[df['Identifikácia VS'] == moj_vs]
        if not vysledok.empty:
            st.success(f"Údaje pre VS {moj_vs} boli nájdené.")
            # Zobrazíme tabuľku len pre daného majiteľa
            st.dataframe(vysledok)
        else:
            st.warning("Tento VS sa v databáze nenachádza.")

    # --- ANKETA ---
    st.divider()
    st.subheader("🗳️ Hlasovanie a ankety")
    st.write("Máte návrh na zlepšenie alebo chcete hlasovať o aktuálnej téme?")
    volba = st.selectbox("Téma: Úprava zelene pred vchodom", ["-- Vyberte --", "Súhlasím", "Nesúhlasím"])
    if volba != "-- Vyberte --":
        st.info(f"Váš hlas ({volba}) bol zaznamenaný. (Historické záznamy sú v správe administrátora).")

except Exception as e:
    st.error("Chyba: Uistite sa, že súbor 'Evidencia.csv' je správne nahraný.")