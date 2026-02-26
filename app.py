import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# ==========================================
# 1. NASTAVENIA
# ==========================================
MOJ_EMAIL = "tvoj@email.com"  # <--- DOPLŇ SVOJ EMAIL
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'

st.set_page_config(page_title="Victory Port - Správa", layout="centered", page_icon="🏡")

def load_data(sheet_name):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    return pd.read_csv(url)

def html_button(link, text, color):
    return f'''
        <a href="{link}" target="_blank" style="text-decoration: none;">
            <div style="background-color:{color};color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;margin-bottom:10px;border:1px solid rgba(255,255,255,0.1);">{text}</div>
        </a>
    '''

try:
    # Načítanie všetkých potrebných hárkov
    df_p = load_data('Platby')
    df_v = load_data('Vydavky')
    try:
        df_h = load_data('Hlasovanie')
    except:
        df_h = pd.DataFrame(columns=['VS', 'Hlas', 'Datum'])

    df_p['Identifikácia VS'] = df_p['Identifikácia VS'].astype(str).str.zfill(4)

    # VÝPOČTY
    prijmy_stlpce = [c for c in df_p.columns if '/26' in c]
    # Vývoj fondu po mesiacoch (pre graf)
    mesacne_prijmy = df_p[prijmy_stlpce].sum()
    celkove_prijmy = mesacne_prijmy.sum()
    celkove_vydavky = pd.to_numeric(df_v['Suma'], errors='coerce').sum()
    zostatok = celkove_prijmy - celkove_vydavky

    # HLAVIČKA
    st.title("🏡 Portál Victory Port")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Fond celkom", f"{celkove_prijmy:.2f} €")
    col_m2.metric("Výdavky", f"{celkove_vydavky:.2f} €")
    col_m3.metric("Zostatok", f"{zostatok:.2f} €")

    # GRAF VÝVOJA FONDU
    st.subheader("📈 Vývoj financií (2026)")
    df_graf = pd.DataFrame({'Mesiac': prijmy_stlpce, 'Príjmy': mesacne_prijmy.values})
    fig = px.line(df_graf, x='Mesiac', y='Príjmy', markers=True, template="plotly_dark", line_shape="spline")
    fig.update_traces(line_color='#1E7E34')
    st.plotly_chart(fig, use_container_width=True)

    # MOJA KONTROLA A HLASOVANIE
    st.divider()
    moj_vs = st.text_input("Zadajte váš Variabilný symbol pre kontrolu a hlasovanie:")

    if moj_vs:
        moj_vs = moj_vs.zfill(4)
        vysledok = df_p[df_p['Identifikácia VS'] == moj_vs]
        
        if not vysledok.empty:
            st.success(f"Dáta pre byt {moj_vs}")
            st.table(vysledok)
            
            # SEKČIA HLASOVANIA
            st.subheader("🗳️ Aktuálne hlasovanie")
            tema = "Súhlasíte s investíciou do novej výsadby zelene (200 €)?"
            st.write(f"**Téma:** {tema}")

            # Zobrazenie priebežného stavu z tabuľky Hlasovanie
            ano_count = len(df_h[df_h['Hlas'] == 'ANO'])
            nie_count = len(df_h[df_h['Hlas'] == 'NIE'])
            
            c_h1, c_h2 = st.columns(2)
            c_h1.info(f"Aktuálne ZA: {ano_count}")
            c_h2.error(f"Aktuálne PROTI: {nie_count}")

            # Tlačidlá
            txt_ano = f"Hlasujem: ANO | VS: {moj_vs}"
            txt_nie = f"Hlasujem: NIE | VS: {moj_vs}"
            link_ano = f"mailto:{MOJ_EMAIL}?subject=HLAS_ANO_VS_{moj_vs}&body={urllib.parse.quote(txt_ano)}"
            link_nie = f"mailto:{MOJ_EMAIL}?subject=HLAS_NIE_VS_{moj_vs}&body={urllib.parse.quote(txt_nie)}"

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(html_button(link_ano, "👍 HLASUJEM ÁNO", "#1E7E34"), unsafe_allow_html=True)
            with col2:
                st.markdown(html_button(link_nie, "👎 HLASUJEM NIE", "#BD2130"), unsafe_allow_html=True)
        else:
            st.error("VS nenájdený.")

    # ZOZNAM DLŽNÍKOV (ANONYMIZOVANÝ)
    st.divider()
    st.subheader("🚨 Prehľad platieb a nedoplatkov")
    # Predpoklad: ak má niekto v aktuálnom mesiaci 0, je dlžník
aktualny_mesiac = prijmy_stlpce[-1] # Posledný pridaný stĺpec
    dlznici = df_p[df_p[aktualny_mesiac] == 0][['Identifikácia VS']]
    
    if not dlznici.empty:
        st.warning(f"Evidujeme chýbajúce platby za {aktualny_mesiac} u týchto VS:")
        st.dataframe(dlznici, hide_index=True, use_container_width=True)
    else:
        st.success("Všetky platby za aktuálny mesiac sú v poriadku.")

    # VÝDAVKY
    st.divider()
    st.subheader("📜 Detailný zoznam výdavkov")
    st.dataframe(df_v, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Chyba: {e}")
