import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# --- NASTAVENIA ---
MOJ_EMAIL = "petermarkuska@gmail.com"  # <--- DOPLŇ SVOJ EMAIL
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

# --- PROGRAM ---
try:
    # Načítanie dát
    df_p = load_data("Platby")
    df_v = load_data("Vydavky")
    try:
        df_h = load_data("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas", "Datum"])

    # Formátovanie VS
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)

    # Finančné výpočty
    p_stlpce = [c for c in df_p.columns if "/26" in c]
    m_sumy = df_p[p_stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    c_prijmy = m_sumy.sum()
    c_vydavky = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum()
    zostatok = c_prijmy - c_vydavky

    # Zobrazenie webu
    st.title("🏡 Portál Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Fond celkom", f"{c_prijmy:.2f} €")
    c2.metric("Výdavky", f"{c_vydavky:.2f} €")
    c3.metric("Zostatok", f"{zostatok:.2f} €")

    # Oprava grafu (zobrazujeme len mesiace s platbou)
    st.subheader("📈 Mesačné príjmy")
    df_graf = pd.DataFrame({"Mesiac": m_sumy.index, "Suma": m_sumy.values})
    df_graf = df_graf[df_graf["Suma"] > 0]
    
    if not df_graf.empty:
        fig = px.line(df_graf, x="Mesiac", y="Suma", markers=True, template="plotly_dark")
        fig.update_traces(line_color="#1E7E34")
        st.plotly_chart(fig, use_container_width=True)

    # Kontrola a Hlasovanie
    st.divider()
    vstup = st.text_input("Zadajte váš VS (napr. 0101):")

    if vstup:
        m_vs = vstup.zfill(4)
        m_data = df_p[df_p["Identifikácia VS"] == m_vs]
        if not m_data.empty:
            st.success(f"Dáta pre VS {m_vs}")
            st.table(m_data)
            
            st.subheader("🗳️ Anketa o zeleni")
            za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
            proti = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
            st.info(f"Priebežné výsledky: 👍 ZA: {za} | 👎 PROTI: {proti}")

            # Mailto odkazy
            l_ano = f"mailto:{MOJ_EMAIL}?subject=HLAS_ANO&body=Hlasujem_ANO_VS_{m_vs}"
            l_nie = f"mailto:{MOJ_EMAIL}?subject=HLAS_NIE&body=Hlasujem_NIE_VS_{m_vs}"

            h1, h2 = st.columns(2)
            with h1:
                st.markdown(f'<a href="{l_ano}" style="text-decoration:none;"><div style="background-color:#1E7E34;color:white;padding:10px;text-align:center;border-radius:5px;">👍 ÁNO</div></a>', unsafe_allow_html=True)
            with h2:
                st.markdown(f'<a href="{l_nie}" style="text-decoration:none;"><div style="background-color:#BD2130;color:white;padding:10px;text-align:center;border-radius:5px;">👎 NIE</div></a>', unsafe_allow_html=True)
        else:
            st.error("VS nenájdený.")

    # Dlžníci
    if p_stlpce:
        st.divider()
        st.subheader("🚨 Chýbajúce platby")
        posl = p_stlpce[-1]
        dlz = df_p[pd.to_numeric(df_p[posl], errors="coerce").fillna(0) == 0][["Identifikácia VS"]]
        if not dlz.empty:
            st.warning(f"Chýba platba za {posl}:")
            st.dataframe(dlz, hide_index=True)

    # Výdavky
    st.divider()
    st.subheader("📜 Zoznam výdavkov")
    st.dataframe(df_v, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Chyba: {e}")
