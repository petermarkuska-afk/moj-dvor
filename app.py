import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time

# --- KONFIGURÁCIA ---
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Postaviť heliport?"
HLAVNE_HESLO = "Victory2026" 

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# --- FUNKCIA NA NAČÍTANIE A OPRAVU DÁT ---
def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        if df.empty:
            return pd.DataFrame()
        
        # 1. Odstránenie bielych znakov z názvov stĺpcov
        df.columns = [str(c).strip() for c in df.columns]
        
        # 2. Inteligentná oprava: Ak sa stĺpec nevolá "VS", ale obsahuje ho (napr. " VS" alebo "VS "), premenuj ho
        for col in df.columns:
            if "VS" in col.upper():
                df.rename(columns={col: "VS"}, inplace=True)
                break
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Chyba načítania hárku {sheet}: {e}")
        return pd.DataFrame()

# --- AUTENTIFIKÁCIA ---
if "auth_pass" not in st.session_state:
    st.session_state["auth_pass"] = False
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# Heslo
if not st.session_state["auth_pass"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte prístupové heslo:", type="password")
    if st.button("Pokračovať", use_container_width=True):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["auth_pass"] = True
            st.rerun()
        else:
            st.error("Nesprávne heslo!")
    st.stop()

# VS Identifikácia (Adresár)
if st.session_state["auth_pass"] and st.session_state["user_data"] is None:
    st.markdown("<h2 style='text-align: center;'>🔑 Identifikácia majiteľa</h2>", unsafe_allow_html=True)
    vs_vstup = st.text_input("Zadajte váš Variabilný symbol (VS):", placeholder="Napr. 1007")
    
    if st.button("Prihlásiť sa"):
        df_a = get_df("Adresar")
        if not df_a.empty and "VS" in df_a.columns:
            df_a["VS"] = df_a["VS"].astype(str).str.strip().str.zfill(4)
            v_search = vs_vstup.strip().zfill(4)
            user_row = df_a[df_a["VS"] == v_search]
            
            if not user_row.empty:
                st.session_state["user_data"] = {
                    "vs": v_search,
                    "meno": str(user_row.iloc[0].get("Meno a priezvisko", "Neznámy")),
                    "email": str(user_row.iloc[0].get("Email", "Neuvedený"))
                }
                st.rerun()
            else:
                st.error(f"VS {v_search} sa v Adresári nenašiel.")
        else:
            st.error("Nepodarilo sa nájsť stĺpec 'VS' v hárku Adresár.")
            if not df_a.empty: st.write("Dostupné stĺpce:", list(df_a.columns))
    st.stop()

# --- PORTÁL ---
try:
    u = st.session_state["user_data"]
    
    # Načítanie dát s ošetrením VS
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")

    # Sidebar
    st.sidebar.markdown(f"### 👤 {u['meno']}")
    st.sidebar.write(f"VS: {u['vs']}")
    if st.sidebar.button("Odhlásiť sa"):
        st.session_state["auth_pass"] = False
        st.session_state["user_data"] = None
        st.rerun()

    st.title("🏡 Správa areálu Victory Port")
    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa"])

    # T1: Nástenka
    with tabs[0]:
        st.markdown("### 📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        st.divider()
        st.markdown("### 🛠️ Podnet pre správcu")
        msg = st.text_area("Napíšte podnet:")
        if msg:
            m_body = f"Od: {u['meno']} (VS:{u['vs']})\nEmail: {u['email']}\n\nSpráva:\n{msg}"
            m_link = f"mailto:{MAIL_SPRAVCA}?subject=Podnet VP {u['vs']}&body={urllib.parse.quote(m_body)}"
            st.link_button("🚀 Odoslať mail správcovi", m_link, use_container_width=True)

    # T2: Financie
    with tabs[1]:
        if not df_p.empty and "VS" in df_p.columns:
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Fond celkom", f"{p_sum:.2f} €")
            c2.metric("Výdavky celkom", f"{v_sum:.2f} €")
            c3.metric("Zostatok", f"{(p_sum - v_sum):.2f} €")
            
            if not df_v.empty and "Dátum" in df_v.columns:
                df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
                df_v["m_fmt"] = df_v["dt"].dt.strftime('%m/%y')
                p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                v_mes = df_v.groupby("m_fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
                df_g = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()})
                st.plotly_chart(px.area(df_g, x="Mesiac", y="Zostatok", template="plotly_dark"), use_container_width=True)
        else:
            st.warning("Dáta o financiách nie sú dostupné (Chýba stĺpec VS v Platbách).")

    # T3: Moje platby
    with tabs[2]:
        st.markdown(f"### 💰 Platby pre VS {u['vs']}")
        if not df_p.empty and "VS" in df_p.columns:
            df_p["VS"] = df_p["VS"].astype(str).str.strip().str.zfill(4)
            moje = df_p[df_p["VS"] == u['vs']]
            if not moje.empty: st.dataframe(moje, hide_index=True)
            else: st.warning("Žiadne záznamy.")
        else:
            st.error("Chyba: V tabuľke 'Platby' sa nenašiel stĺpec 'VS'.")

    # T4: Anketa
    with tabs[3]:
        if OTAZKA.upper() != "ŽIADNA ANKETA":
            st.subheader(OTAZKA)
            if not df_h.empty:
                h_col = next((c for c in df_h.columns if "HLAS" in c.upper()), df_h.columns[-1])
                za = len(df_h[df_h[h_col].astype(str).str.upper().str.contains("ANO")])
                ni = len(df_h[df_h[h_col].astype(str).str.upper().str.contains("NIE")])
                ca, cb = st.columns(2); ca.metric("ZA", za); cb.metric("PROTI", ni)
            
            b1, b2 = st.columns(2)
            b1.link_button("👍 ZA", f"mailto:{MAIL_SPRAVCA}?subject=HLAS_ANO_{u['vs']}")
            b2.link_button("👎 PROTI", f"mailto:{MAIL_SPRAVCA}?subject=HLAS_NIE_{u['vs']}")
        else:
            st.info("Žiadna anketa.")

except Exception as e:
    st.error(f"Vyskytla sa neočakávaná chyba: {e}")

st.caption("© 2026 Správa areálu Victory Port")
