import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURÁCIA ---
MAIL = "tvoj@email.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

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

    # 2. LOGIKA FINANCIÍ (Odolná voči chybám)
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce_m = [c for c in df_p.columns if "/26" in c]
    
    # Mesačné sumy
    p_mesacne = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Dátum" in df_v.columns:
        df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
        df_v["Mes_Fmt"] = df_v["dt"].dt.strftime('%m/%y')
        v_mesacne = df_v.groupby("Mes_Fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
    else:
        v_mesacne = pd.Series(0, index=stlpce_m)

    # Kumulatívny zostatok
    df_graf = pd.DataFrame({
        "Mesiac": stlpce_m,
        "Zostatok": (p_mesacne.values - v_mesacne.values).cumsum()
    })
    df_graf = df_graf[p_mesacne > 0]

    # --- ZOBRAZENIE PODĽA POŽIADAVIEK ---

    # 1. Názov
    st.markdown("<h1 style='text-align: center;'>🏡 Portál správcu VICTORY PORT</h1>", unsafe_allow_html=True)
    st.write("---")

    # 2. Súčty a Graf
    c1, c2, c3 = st.columns(3)
    c_p = p_mesacne.sum()
    c_v = df_v["Suma"].sum()
    c1.metric("Fond celkom", f"{c_p:.2f} €")
    c2.metric("Výdavky celkom", f"{c_v:.2f} €")
    c3.metric("Aktuálny zostatok", f"{(c_p - c_v):.2f} €")

    if not df_graf.empty:
        fig = px.area(df_graf, x="Mesiac", y="Zostatok", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # 3. IDENTIFIKUJ SA
    st.write("---")
    st.subheader("🔐 IDENTIFIKUJ SA")
    vstup = st.text_input("Zadajte váš variabilný symbol (4 číslice):")

    if vstup:
        vs_clean = vstup.zfill(4)
        moje_data = df_p[df_p["Identifikácia VS"] == vs_clean]
        
        if not moje_data.empty:
            st.success(f"Overené. Vitajte, vlastník priestoru {vs_clean}")
            st.dataframe(moje_data, hide_index=True)
            
            # 4. ANKETA (Zobrazí sa až po overení)
            st.divider()
            st.subheader("🗳️ Aktuálne hlasovanie")
            st.info("**Otázka:** Súhlasíte s realizáciou nových bezpečnostných kamier v objekte?")
            
            # Štatistika z tabuľky Hlasovanie
            za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
            nie = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
            
            s1, s2 = st.columns(2)
            s1.metric("Hlasov ZA", za)
            s2.metric("Hlasov PROTI", nie)

            st.write("Kliknutím na tlačidlo nižšie sa vám predpripraví e-mail:")
            
            # Generovanie mailto odkazov
            body_ano = f"Hlasujem_ZA_za_jednotku_VS_{vs_clean}"
            body_nie = f"Hlasujem_PROTI_za_jednotku_VS_{vs_clean}"
            
            l_ano = f"mailto:{MAIL}?subject=HLAS_ANO_VS_{vs_clean}&body={body_ano}"
            l_nie = f"mailto:{MAIL}?subject=HLAS_NIE_VS_{vs_clean}&body={body_nie}"
            
            b1, b2 = st.columns(2)
            b1.link_button("👍 HLASUJEM ZA", l_ano, use_container_width=True)
            b2.link_button("👎 HLASUJEM PROTI", l_nie, use_container_width=True)
        else:
            st.error("Tento variabilný symbol neevidujeme. Skúste znova.")

    # 5. Výdavky úplne naspodku (nepovinné zobrazenie)
    st.write("---")
    with st.expander("📜 Zobraziť zoznam výdavkov"):
        st.dataframe(df_v[["Dátum", "Účel", "Suma"]], hide_index=True, use_container_width=True)

except Exception as e:
    st.warning(f"Načítavam dáta alebo čakám na vstup... (Detaily: {e})")
