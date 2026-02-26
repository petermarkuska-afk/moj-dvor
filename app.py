import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# --- SETUP ---
MAIL = "tvoj@email.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered")

def get_data(name):
    u = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={name}"
    return pd.read_csv(u)

try:
    # 1. NACITANIE
    df_p = get_data("Platby")
    df_v = get_data("Vydavky")
    try:
        df_h = get_data("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. LOGIKA FINANCII
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce = [c for c in df_p.columns if "/26" in c]
    
    # Prijmy a vydavky na casovej osi
    m_p = df_p[stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Mesiac" in df_v.columns:
        m_v = df_v.groupby("Mesiac")["Suma"].sum()
    else:
        m_v = pd.Series(0, index=m_p.index)

    c_prijmy = m_p.sum()
    c_vydavky = df_v["Suma"].sum()
    zost = c_prijmy - c_vydavky

    # 3. VIZUAL - HLAVICKA
    st.title("🏡 Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Prijmy", f"{c_prijmy:.2f} €")
    c2.metric("Vydavky", f"{c_vydavky:.2f} €")
    c3.metric("Zostatok", f"{zost:.2f} €")

    # 4. GRAF REALNEHO ZOSTATKU
    st.write("---")
    st.subheader("📈 Realny stav fondu (po odratani vydavkov)")
    
    # Vypocet: (Prijmy v danom mesiaci - Vydavky v danom mesiaci) a potom sumarny sucet
    df_g = pd.DataFrame(index=m_p.index)
    df_g["Prijem"] = m_p.values
    df_g["Vydaj"] = m_v.reindex(m_p.index, fill_value=0).values
    df_g["Bilancia"] = df_g["Prijem"] - df_g["Vydaj"]
    df_g["Realny_Zostatok"] = df_g["Bilancia"].cumsum()
    
    df_g = df_g[df_g["Prijem"] > 0].reset_index()
    
    if not df_g.empty:
        fig = px.area(df_g, x="index", y="Realny_Zostatok", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
        st.plotly_chart(fig, use_container_width=True)

    # 5. ANKETA (Viditelna hned)
    st.write("---")
    st.subheader("🗳️ Celkove vysledky ankety")
    v_za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
    v_pr = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
    st.info(f"Aktualny stav: 👍 ZA: {v_za} | 👎 PROTI: {v_pr}")

    # 6. KONTROLA A HLASOVANIE (Po zadani VS)
    st.write("---")
    v_in = st.text_input("Pre hlasovanie a kontrolu zadajte Vas VS:")
    if v_in:
        vs = v_in.zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == vs]
        if not moje.empty:
            st.success(f"Vase platby (VS {vs})")
            st.table(moje)
            
            st.write("### Odošlite Váš hlas:")
            l1 = f"mailto:{MAIL}?subject=HLAS_ANO_VS_{vs}&body=Hlasujem_ANO"
            l2 = f"mailto:{MAIL}?subject=HLAS_NIE_VS_{vs}&body=Hlasujem_NIE"
            
            cx, cy = st.columns(2)
            cx.link_button("👍 HLASUJEM ZA", l1, use_container_width=True)
            cy.link_button("👎 HLASUJEM PROTI", l2, use_container_width=True)
            
            with st.expander("Nefunguju Vam tlacitla? (Instrukcia pre Gmail)"):
                st.write(f"Poslite email na: **{MAIL}**")
                st.write(f"Predmet (skopirujte): `HLAS_ANO_VS_{vs}` (alebo NIE)")
                st.write("Telo mailu: `Hlasujem za/proti`.")
        else:
            st.error("VS nenajdeny.")

    # 7. DLZNICI A VYDAVKY
    if stlpce:
        st.write("---")
        posl_m = stlpce[-1]
        dlz = df_p[pd.to_numeric(df_p[posl_m], errors="coerce").fillna(0) == 0]
        if not dlz.empty:
            st.warning(f"🚨 Chybajuce platby za {posl_m}:")
            st.dataframe(dlz[["Identifikácia VS"]], hide_index=True)

    st.write("---")
    st.subheader("📜 Zoznam vydavkov")
    st.dataframe(df_v, hide_index=True)

except Exception as e:
    st.error(f"Chyba: {e}")
