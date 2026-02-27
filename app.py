import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURÁCIA ---
MAIL = "tvoj@email.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Súhlasíte s investíciou do modernizácie osvetlenia?"
HLAVNE_HESLO = "Victory2026" 

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

# --- ZÁMOK STRÁNKY ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte heslo:", type="password")
    if st.button("Vstúpiť", use_container_width=True):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Nesprávne heslo!")
    st.stop()

# --- NAČÍTANIE DÁT ---
def get_df(sheet):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}"
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

try:
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")

    # 1. ČISTENIE DÁT PRE FINANCIE
    if not df_p.empty:
        df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.strip().str.zfill(4)
        stlpce_m = [c for c in df_p.columns if "/26" in c]
        p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    else:
        p_mes = pd.Series()

    if not df_v.empty:
        df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)

    # --- UI HLAVIČKA ---
    st.title("🏡 Victory Port")
    if st.button("Odhlásiť"):
        st.session_state["authenticated"] = False
        st.rerun()
    st.write("---")

    # METRIKY A GRAF
    if not p_mes.empty:
        m1, m2, m3 = st.columns(3)
        v_sum = df_v["Suma"].sum() if not df_v.empty else 0
        m1.metric("Fond celkom", f"{p_mes.sum():.2f} €")
        m2.metric("Výdavky celkom", f"{v_sum:.2f} €")
        m3.metric("Aktuálny zostatok", f"{(p_mes.sum() - v_sum):.2f} €")

        if "Dátum" in df_v.columns and not df_v.empty:
            df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
            df_v["m_fmt"] = df_v["dt"].dt.strftime('%m/%y')
            v_mes = df_v.groupby("m_fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
        else:
            v_mes = pd.Series(0, index=stlpce_m)

        df_graf = pd.DataFrame({
            "Mesiac": stlpce_m, 
            "Zostatok": (p_mes.values - v_mes.values).cumsum()
        }).reset_index(drop=True)
        df_graf = df_graf[p_mes.values > 0]
        
        if not df_graf.empty:
            fig = px.area(df_graf, x="Mesiac", y="Zostatok", template="plotly_dark")
            fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
            st.plotly_chart(fig, use_container_width=True)

    # --- SEKČIA POUŽÍVATEĽA ---
    st.write("---")
    vs_in = st.text_input("Zadajte váš VS (4 číslice):")
    
    if vs_in:
        v_c = vs_in.strip().zfill(4)
