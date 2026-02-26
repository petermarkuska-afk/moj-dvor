import streamlit as st
import pandas as pd
import plotly.express as px

# --- ZÁKLADNÉ NASTAVENIA ---
MAIL = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered")

def get_df(sheet):
    url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}"
    return pd.read_csv(url)

try:
    # 1. NAČÍTANIE DÁT
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    try:
        df_h = get_df("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. FINANČNÁ LOGIKA
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce_mesiacov = [c for c in df_p.columns if "/26" in c]
    
    # Príjmy po mesiacoch
    prijmy_mesacne = df_p[stlpce_mesiacov].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    
    # Výdavky po mesiacoch (MUSÍŠ mať stĺpec 'Mesiac' v hárku Vydavky!)
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    if "Mesiac" in df_v.columns:
        vydavky_mesacne = df_v.groupby("Mesiac")["Suma"].sum()
    else:
        vydavky_mesacne = pd.Series(0, index=prijmy_mesacne.index)

    celkove_prijmy = prijmy_mesacne.sum()
    celkove_vydavky = df_v["Suma"].sum()
    aktualny_zostatok = celkove_prijmy - celkove_vydavky

    # 3. HLAVNÝ PANEL
    st.title("🏡 Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Príjmy", f"{celkove_prijmy:.2f} €")
    c2.metric("Výdavky", f"{celkove_vydavky:.2f} €")
    c3.metric("Zostatok", f"{aktualny_zostatok:.2f} €")

    # 4. GRAF REÁLNEHO ZOSTATKU (OPRAVENÝ)
    st.write("---")
    st.subheader("📈 Reálny stav fondu v čase")
    
    df_graf = pd.DataFrame(index=prijmy_mesacne.index)
    df_graf["Prijem"] = prijmy_mesacne.values
    df_graf["Vydaj"] = vydavky_mesacne.reindex(prijmy_mesacne.index, fill_value=0).values
    # Kľúč k úspechu: Odpočítame výdavky od príjmov a urobíme kumulatívny súčet
    df_graf["Bilancia"] = df_graf["Prijem"] - df_graf["Vydaj"]
    df_graf["Zostatok"] = df_graf["Bilancia"].cumsum()
    
    df_graf = df_graf[df_graf["Prijem"] > 0].reset_index()
    
    if not df_graf.empty:
        fig = px.area(df_graf, x="index", y="Zostatok", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
        fig.update_layout(xaxis_title="Mesiac", yaxis_title="Zostatok v €")
        st.plotly_chart(fig, use_container_width=True)

    # 5. ANKETA (Viditeľná ihneď)
    st.write("---")
    st.subheader("🗳️ Priebežné výsledky ankety")
    za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
    proti = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
    st.info(f"Stav hlasovania: 👍 ÁNO: {za} | 👎 NIE: {proti}")

    # 6. KONTROLA A HLASOVANIE
    st.write("---")
    moj_vs = st.text_input("Zadajte váš VS pre hlasovanie a kontrolu:")
    if moj_vs:
        vs_clean = moj_vs.zfill(4)
        vlastne_data = df_p[df_p["Identifikácia VS"] == vs_clean]
        if not vlastne_data.empty:
            st.table(vlastne_data)
            
            st.write("### Hlasujte kliknutím:")
            url_ano = f"mailto:{MAIL}?subject=HLAS_ANO_VS_{vs_clean}&body=Hlasujem_ANO"
            url_nie = f"mailto:{MAIL}?subject=HLAS_NIE_VS_{vs_clean}&body=Hlasujem_NIE"
            
            btn1, btn2 = st.columns(2)
            btn1.link_button("👍 HLASUJEM ÁNO", url_ano, use_container_width=True)
            btn2.link_button("👎 HLASUJEM NIE", url_nie, use_container_width=True)
            
            with st.expander("Nefungujú tlačidlá? (Manuálny návod)"):
                st.write(f"Pošlite email na: **{MAIL}**")
                st.write(f"Predmet: `HLAS_ANO_VS_{vs_clean}`")
                st.write("Text: Hlasujem za/proti.")
        else:
            st.error("VS nenájdený.")

    # 7. DLŽNÍCI A VÝDAVKY
    if stlpce_mesiacov:
        st.write("---")
        posledny = stlpce_mesiacov[-1]
        dlznici = df_p[pd.to_numeric(df_p[posledny], errors="coerce").fillna(0) == 0]
        if not dlznici.empty:
            st.warning(f"🚨 Chýbajúce platby za {posledny}:")
            st.dataframe(dlznici[["Identifikácia VS"]], hide_index=True)

    st.write("---")
    st.subheader("📜 Detailný zoznam výdavkov")
    st.dataframe(df_v, hide_index=True)

except Exception as e:
    st.error(f"Chyba v aplikácii: {e}")
