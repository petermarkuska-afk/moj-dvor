import streamlit as st
import pandas as pd

st.set_page_config(page_title="Správa nášho dvora", layout="centered")

# --- FUNKCIA NA NAČÍTANIE ---
def load_data():
    df_platby = pd.read_csv('Evidencia.csv')
    df_platby['Identifikácia VS'] = df_platby['Identifikácia VS'].astype(str).str.zfill(4)
    
    # Skúsime načítať výdavky, ak existujú
    try:
        df_vydavky = pd.read_csv('Vydavky.csv')
    except:
        df_vydavky = pd.DataFrame(columns=['Dátum', 'Popis', 'Suma'])
        
    return df_platby, df_vydavky

try:
    df_p, df_v = load_data()

    # --- VÝPOČTY ---
    prijmy_stlpce = df_p.columns[1:13]
    celkove_prijmy = df_p[prijmy_stlpce].sum().sum()
    celkove_vydavky = df_v['Suma'].sum()
    zostatok = celkove_prijmy - celkove_vydavky

    # --- ZOBRAZENIE ---
    st.title("🏡 Portál správy spoločného dvora")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Celkové príjmy", f"{celkove_prijmy:.2f} €")
    c2.metric("Celkové výdavky", f"{celkove_vydavky:.2f} €")
    c3.metric("Aktuálny zostatok", f"{zostatok:.2f} €", delta_color="normal")

    # --- SEKČIA PRE VLASTNÍKA ---
    st.divider()
    st.subheader("🔎 Moja kontrola platieb")
    moj_vs = st.text_input("Zadajte váš Variabilný symbol (napr. 0105):")

    if moj_vs:
        vysledok = df_p[df_p['Identifikácia VS'] == moj_vs]
        if not vysledok.empty:
            st.success(f"Dáta pre VS {moj_vs}:")
            st.dataframe(vysledok)
            
            # Kontrola, či zaplatil aktuálny mesiac (február)
            if vysledok['02/26'].values[0] <= 0:
                st.error("⚠️ Pre tento mesiac (02/26) neevidujeme vašu platbu.")
            else:
                st.info("✅ Platba za aktuálny mesiac je v poriadku.")
        else:
            st.warning("Tento VS sa v databáze nenachádza.")

    # --- TABUĽKA VÝDAVKOV ---
    st.divider()
    st.subheader("📜 Zoznam výdavkov areálu")
    st.table(df_v)

except Exception as e:
    st.error(f"Chyba pri načítaní dát: {e}")
