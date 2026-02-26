import streamlit as st
import pandas as pd
import urllib.parse

# ==========================================
# 1. NASTAVENIA
# ==========================================
MOJ_EMAIL = "petermarkuska@gmail.com"  # <--- SEM NAPÍŠ SVOJ EMAIL
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'

st.set_page_config(page_title="Správa nášho dvora", layout="centered", page_icon="🏡")

def load_data(sheet_name):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    return pd.read_csv(url)

# pomocná funkcia pre štýl tlačidiel
def html_button(link, text, color):
    return f'''
        <a href="{link}" target="_blank" style="text-decoration: none;">
            <div style="
                background-color: {color};
                color: white;
                padding: 12px;
                text-align: center;
                border-radius: 8px;
                font-weight: bold;
                font-family: sans-serif;
                margin-bottom: 10px;
                border: 1px solid rgba(255,255,255,0.1);
            ">
                {text}
            </div>
        </a>
    '''

try:
    df_p = load_data('Platby')
    df_v = load_data('Vydavky')
    df_p['Identifikácia VS'] = df_p['Identifikácia VS'].astype(str).str.zfill(4)

    # VÝPOČTY
    prijmy_stlpce = [c for c in df_p.columns if '/26' in c]
    celkove_prijmy = pd.to_numeric(df_p[prijmy_stlpce].stack(), errors='coerce').sum()
    celkove_vydavky = pd.to_numeric(df_v['Suma'], errors='coerce').sum()
    zostatok = celkove_prijmy - celkove_vydavky

    # ZOBRAZENIE
    st.title("🏡 Portál správy spoločného dvora")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Celkové príjmy", f"{celkove_prijmy:.2f} €")
    c2.metric("Celkové výdavky", f"{celkove_vydavky:.2f} €")
    c3.metric("Aktuálny zostatok", f"{zostatok:.2f} €")

    st.divider()
    st.subheader("🔎 Moja kontrola platieb")
    moj_vs = st.text_input("Zadajte váš Variabilný symbol (napr. 0101):")

    if moj_vs:
        vysledok = df_p[df_p['Identifikácia VS'] == moj_vs]
        if not vysledok.empty:
            st.table(vysledok)
        else:
            st.warning("VS sa nenašiel.")

    # SEKČIA HLASOVANIE
    st.divider()
    st.subheader("🗳️ Aktuálne hlasovanie")
    tema = "Súhlasíte s investíciou do novej výsadby zelene (200 €)?"
    st.write(f"**Téma:** {tema}")
    
    if moj_vs:
        # Farby: Tmavšia zelená a tlmenejšia červená
        color_ano = "#1E7E34" 
        color_nie = "#BD2130"

        txt_ano = f"Hlasujem: ANO | VS: {moj_vs}"
        txt_nie = f"Hlasujem: NIE | VS: {moj_vs}"
        
        # Odkazy pre poštové aplikácie
        link_ano = f"mailto:{MOJ_EMAIL}?subject=HLAS_ANO_VS_{moj_vs}&body={urllib.parse.quote(txt_ano)}"
        link_nie = f"mailto:{MOJ_EMAIL}?subject=HLAS_NIE_VS_{moj_vs}&body={urllib.parse.quote(txt_nie)}"

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(html_button(link_ano, "👍 HLASUJEM ÁNO", color_ano), unsafe_allow_html=True)
        with col2:
            st.markdown(html_button(link_nie, "👎 HLASUJEM NIE", color_nie), unsafe_allow_html=True)

        # RIEŠENIE PRE GMAIL WEB (MANUÁLNE KOPÍROVANIE)
        with st.expander("Nefungujú vám tlačidlá? (Pre používateľov Gmail v prehliadači)"):
            st.write(f"Ak sa vám po kliknutí neotvoril e-mail, pošlite správu manuálne na: **{MOJ_EMAIL}**")
            st.code(f"Predmet: HLAS_VS_{moj_vs}\nText: {txt_ano} (alebo NIE)")
            st.info("Stačí skopírovať tento text a poslať ho z vášho Gmailu.")
    else:
        st.info("Zadajte svoj VS hore, aby sa zobrazili hlasovacie tlačidlá.")

    st.divider()
    st.subheader("📜 Detailný zoznam výdavkov")
    st.dataframe(df_v, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Dáta sa nepodarilo načítať. {e}")

