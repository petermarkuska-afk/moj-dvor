import streamlit as st
import pandas as pd
import plotly.express as px

# --- NASTAVENIA ---
MAIL = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered")

def get_df(sheet):
    url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}"
    return pd.read_csv(url)

try:
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    try:
        df_h = get_df("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 1. PRÍPRAVA DÁT PRÍJMOV
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce_m = [c for c in df_p.columns if "/26" in c]
    m_prijmy = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()

    # 2. INTELIGENTNÉ SPRACOVANIE VÝDAVKOV Z DÁTUMU
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Dátum" in df_v.columns:
        # Prevod textového dátumu na skutočný dátum a potom na formát MM/YY (napr. 02/26)
        df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
        df_v["Mesiac_Format"] = df_v["dt"].dt.strftime('%m/%y')
        m_vydavky = df_v.groupby("Mesiac_Format")["Suma"].sum().reindex(stlpce_m, fill_value=0)
    else:
        m_vydavky = pd.Series(0, index=stlpce_m)

    # 3. VÝPOČET REÁLNEHO ZOSTATKU
    df_graf = pd.DataFrame({
        "Mesiac": stlpce_m,
        "Príjmy": m_prijmy.values,
        "Výdavky": m_vydavky.values
    })
    df_graf["Bilancia"] = df_graf["Príjmy"] - df_graf["Výdavky"]
    df_graf["Zostatok"] = df_graf["Bilancia"].cumsum()
    
    # Zobrazenie len doterajších mesiacov
    df_graf = df_graf[df_graf["Príjmy"] > 0]

    # 4. DASHBOARD
    st.title("🏡 Portál Victory Port")
    
    # Anketa hneď navrchu
    za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
    nie = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
    st.info(f"🗳️ Aktuálny stav hlasovania: ÁNO: {za} | NIE: {nie}")
    st.write("---")

    c1, c2, c3 = st.columns(3)
    c1.metric("Príjmy", f"{m_prijmy.sum():.2f} €")
    c2.metric("Výdavky", f"{df_v['Suma'].sum():.2f} €")
    c3.metric("Zostatok", f"{(m_prijmy.sum() - df_v['Suma'].sum()):.2f} €")

    st.subheader("📈 Reálny stav fondu (Bilancia)")
    if not df_graf.empty:
        fig = px.area(df_graf, x="Mesiac", y="Zostatok", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
        st.plotly_chart(fig, use_container_width=True)

    # 5. KONTROLA VS A HLASOVANIE
    st.write("---")
    vstup = st.text_input("Zadajte VS pre kontrolu a hlasovanie:")
    if vstup:
        vs_c = vstup.zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == vs_c]
        if not moje.empty:
            st.success(f"Dáta pre VS {vs_c}")
            st.table(moje)
            
            st.write("### Hlasujte cez email:")
            l1 = f"mailto:{MAIL}?subject=HLAS_ANO_VS_{vs_c}&body=Hlasujem_ANO"
            l2 = f"mailto:{MAIL}?subject=HLAS_NIE_VS_{vs_c}&body=Hlasujem_NIE"
            
            col_a, col_b = st.columns(2)
            col_a.link_button("👍 HLASUJEM ÁNO", l1, use_container_width=True)
            col_b.link_button("👎 HLASUJEM NIE", l2, use_container_width=True)
            
            with st.expander("Návod na manuálne hlasovanie"):
                st.write(f"Príjemca: {MAIL}")
                st.write(f"Predmet: `HLAS_ANO_VS_{vs_c}` (alebo NIE)")
        else:
            st.error("VS nebol nájdený.")

    # 6. DETAIL VÝDAVKOV
    st.write("---")
    st.subheader("📜 Zoznam všetkých výdavkov")
    st.dataframe(df_v[["Dátum", "Účel", "Suma"]], hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"Vyskytla sa chyba: {e}")
