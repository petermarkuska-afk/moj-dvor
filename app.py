import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# Nastavenia
EMAIL = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered")

def get_data(name):
    u = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={name}"
    return pd.read_csv(u)

try:
    # 1. Nacitanie dat
    p = get_data("Platby")
    v = get_data("Vydavky")
    try:
        h = get_data("Hlasovanie")
    except:
        h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. Vypocty
    p["Identifikácia VS"] = p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce = [c for c in p.columns if "/26" in c]
    
    m_prijmy = p[stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    v["Suma"] = pd.to_numeric(v["Suma"], errors="coerce").fillna(0)
    
    # Vypocet vydavkov podla mesiacov
    if "Mesiac" in v.columns:
        m_vydavky = v.groupby("Mesiac")["Suma"].sum()
    else:
        m_vydavky = pd.Series(0, index=m_prijmy.index)

    c_prijmy = m_prijmy.sum()
    c_vydavky = v["Suma"].sum()
    zostatok = c_prijmy - c_vydavky

    # 3. Zobrazenie
    st.title("Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Prijmy", f"{c_prijmy:.2f} E")
    c2.metric("Vydavky", f"{c_vydavky:.2f} E")
    c3.metric("Zostatok", f"{zostatok:.2f} E")

    # 4. Graf zostatku
    st.subheader("Vyvoj zostatku")
    df_g = pd.DataFrame(index=m_prijmy.index)
    df_g["Zisk"] = m_prijmy.values - m_vydavky.reindex(m_prijmy.index, fill_value=0).values
    df_g["Zostatok"] = df_g["Zisk"].cumsum()
    df_g = df_g[m_prijmy > 0].reset_index()
    df_g.columns = ["Mesiac", "Zisk", "Zostatok"]

    if not df_g.empty:
        fig = px.area(df_g, x="Mesiac", y="Zostatok", template="plotly_dark")
        fig.update_traces(line_color="#1E7E34")
        st.plotly_chart(fig, use_container_width=True)

    # 5. Hlasovanie
    st.divider()
    vstup = st.text_input("Zadajte VS:")
    if vstup:
        vs_clean = vstup.zfill(4)
        moje = p[p["Identifikácia VS"] == vs_clean]
        if not moje.empty:
            st.write("Vase platby:")
            st.table(moje)
            
            st.subheader("Hlasovanie")
            v_za = len(h[h["Hlas"].astype(str).str.contains("ANO", na=False)])
            v_pr = len(h[h["Hlas"].astype(str).str.contains("NIE", na=False)])
            st.info(f"Stav: ZA: {v_za} | PROTI: {v_pr}")

            m_za = f"mailto:{EMAIL}?subject=ANO_VS_{vs_clean}"
            m_pr = f"mailto:{EMAIL}?subject=NIE_VS_{vs_clean}"
            
            ca, cb = st.columns(2)
            ca.link_button("HLASUJEM ZA", m_za, use_container_width=True)
            cb.link_button("HLASUJEM PROTI", m_pr, use_container_width=True)

    # 6. Dlznici
    if stlpce:
        st.divider()
        posl = stlpce[-1]
        d_p = p.copy()
        d_p[posl] = pd.to_numeric(d_p[posl], errors="coerce").fillna(0)
        dlznici = d_p[d_p[posl] == 0][["Identifikácia VS"]]
        if not dlznici.empty:
            st.warning(f"Chybaju platby za {posl}:")
            st.dataframe(dlznici, hide_index=True)

    # 7. Vydavky
    st.divider()
    st.subheader("Zoznam vydavkov")
    st.dataframe(v, hide_index=True)

except Exception as e:
    st.error(f"Chyba: {e}")
