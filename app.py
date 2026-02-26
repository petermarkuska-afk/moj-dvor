import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# ==========================================
# 1. NASTAVENIA
# ==========================================
MOJ_EMAIL = "petermarkuska@gmail.com"  # <--- SEM DOPLŇ SVOJ EMAIL
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

def load_data(sheet_name):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    return pd.read_csv(url)

def html_button(link, text, color):
    return f'''
        <a href="{link}" target="_blank" style="text-decoration: none;">
            <div style="background-color:{color};color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;margin-bottom:10px;border:1px solid rgba(255,255,255,0.1);">{text}</div>
        </a>
    '''

# ==========================================
# 2. HLAVNÝ BLOK (TRY / EXCEPT)
# ==========================================
try:
    # NAČÍTANIE DÁT
    df_p = load_data('Platby')
    df_v = load_data('Vydavky')
    
    # Skúsime načítať hlasovanie, ak neexistuje, vytvoríme prázdne
    try:
        df_h = load_data('Hlasovanie')
    except:
        df_h = pd.DataFrame(columns=['VS', 'Hlas', 'Datum'])

    # Ošetrenie VS
    df_p['Identifikácia VS'] = df_p['Identifikácia VS'].astype(str).str.zfill(4)

    # VÝPOČTY
    prijmy_stlpce = [c for c in df_p.columns if '/26' in c]
    mesacne_sumy = df_p[prijmy_stlpce].sum()
    celkove_prijmy = mesacne_sumy.sum()
    celkove_vydavky = pd.to_numeric(df_v['Suma'], errors='coerce').sum()
    zostatok = celkove_prijmy - celkove_vydavky

    # ZOBRAZENIE METRÍK
    st.title("🏡 Portál Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Fond", f"{celkove_prijmy:.2f} €")
    c2.metric("Výdavky", f"{celkove_vydavky:.2f} €")
    c3.metric("Zostatok", f"{zostatok:.2f} €")

    # GRAF
    st.subheader("📈 Vývoj príjmov")
    if not mesacne_sumy.empty:
        df_graf = pd.DataFrame({'Mesiac': mesacne_sumy.index, 'Suma': mesacne_sumy.values})
        fig = px.line(df_graf, x='Mesiac', y='Suma', markers=True, template="plotly_dark")
        fig.update_traces(line_color='#1E7E34')
        st.plotly_chart(fig, use_container_width=True)

    # KONTROLA A HLASOVANIE
    st.divider()
    vs_vstup = st.text_input("Zadajte váš VS (napr. 0101):")

    if vs_vstup:
        moj_vs = vs_vstup.zfill(4)
        moje_data = df_p[df_p['Identifikácia VS'] == moj_vs]
        
        if not moje_data.empty:
            st.success(f"Dááta pre byt {moj_vs}")
            st.table(moje_data)
            
            # HLASOVANIE
            st.subheader("🗳️ Anketa")
            st.write("Téma: Súhlasíte s investíciou do novej výsadby zelene?")
            
            # Sčítanie hlasov (priebežný stav)
            ano = len(df_h[df_h['Hlas'].str.contains('ANO', na=False, case=False)])
            nie = len(df_h[df_h['Hlas'].str.contains('NIE', na=False, case=False)])
            
            st.info(f"Priebežné výsledky: 👍 ZA: {ano} | 👎 PROTI: {nie}")

            t_ano = f"Hlasujem ANO | VS: {moj_vs}"
            t_nie = f"Hlasujem NIE | VS: {moj_vs}"
            
            l_ano = f"mailto:{MOJ_EMAIL}?subject=HLAS_ANO&body={urllib.parse.quote(t_ano)}"
            l_nie = f"mailto:{MOJ_EMAIL}?subject=HLAS_NIE&body={urllib.parse.quote(t_nie)}"

            h_col1, h_col2 = st.columns(2)
            with h_col1:
                st.markdown(html_button(l_ano, "👍 HLASUJEM ÁNO", "#1E7E34"), unsafe_allow_html=True)
            with h_col2:
                st.markdown(html_button(l_nie, "👎 HLASUJEM NIE", "#BD2130"), unsafe_allow_html=True)
        else:
            st.error("Tento VS sa v zozname nenachádza.")

    # ZOZNAM DLŽNÍKOV
    if prijmy_stlpce:
        st.divider()
        st.subheader("🚨 Chýbajúce platby")
        posledny = prijmy_stlpce[-1]
        dlh = df_p[pd.to_numeric(df_p[posledny], errors='coerce').fillna(0) == 0][['Identifikácia VS']]
        if not dlh.empty:
            st.warning(f"Neevidujeme platbu za {posledny}:")
            st.dataframe(dlh, hide_index=True, use_container_width=True)
        else:
            st.success(f"Všetky platby za {posledny} sú v poriadku.")

    # VÝDAVKY
    st.divider()
    st.subheader("📜 Detailný zoznam výdavkov")
    st.dataframe(df_v, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Chyba pri načítaní dát: {e}")
    st.info("Skontrolujte, či v Google tabuľke existujú hárky 'Platby', 'Vydavky' a 'Hlasovanie'.")
