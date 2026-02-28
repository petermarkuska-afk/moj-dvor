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

st.set_page_config(page_title="Správa areálu Victory Port", layout="wide", page_icon="🏡")

# --- FUNKCIA NA NAČÍTANIE A ČISTENIE DÁT ---
def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        # Odstránenie bielych znakov z názvov stĺpcov pre elimináciu KeyError
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- AUTENTIFIKÁCIA ---
if "auth_pass" not in st.session_state:
    st.session_state["auth_pass"] = False
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# 1. Hlavné heslo
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

# 2. Identifikácia cez Adresár
if st.session_state["auth_pass"] and st.session_state["user_data"] is None:
    st.markdown("<h2 style='text-align: center;'>🔑 Identifikácia majiteľa</h2>", unsafe_allow_html=True)
    vs_vstup = st.text_input("Zadajte váš Variabilný symbol (VS):", placeholder="Napr. 1007")
    
    if st.button("Prihlásiť sa"):
        df_a = get_df("Adresar")
        if not df_a.empty:
            # Hľadáme stĺpec VS (ošetrené proti KeyError)
            vs_col = next((c for c in df_a.columns if "VS" in c.upper()), None)
            if vs_col:
                df_a[vs_col] = df_a[vs_col].astype(str).str.strip().str.zfill(4)
                target_vs = vs_vstup.strip().zfill(4)
                user_row = df_a[df_a[vs_col] == target_vs]
                
                if not user_row.empty:
                    st.session_state["user_data"] = {
                        "vs": target_vs,
                        "meno": str(user_row.iloc[0].get("Meno a priezvisko", "Neznámy")),
                        "email": str(user_row.iloc[0].get("Email", "Email neuvedený"))
                    }
                    st.rerun()
                else:
                    st.error(f"VS {target_vs} sa v Adresári nenašiel.")
            else:
                st.error("V hárku 'Adresar' chýba stĺpec 'VS'.")
    st.stop()

# --- PORTÁL (PO PRIHLÁSENÍ) ---
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")

    # Sidebar s kompletnými údajmi
    st.sidebar.markdown(f"### 👤 Prihlásený")
    st.sidebar.info(f"**{u['meno']}**\n\nVS: {u['vs']}\n\n📧 {u['email']}")
    if st.sidebar.button("Odhlásiť sa"):
        st.session_state["auth_pass"] = False
        st.session_state["user_data"] = None
        st.rerun()

    st.title("🏡 Správa areálu Victory Port")
    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa"])

    # --- T1: NÁSTENKA ---
    with tabs[0]:
        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        
        st.divider()
        st.subheader("🛠️ Podnet pre správcu")
        podnet_text = st.text_area("Popíšte váš podnet:", placeholder="Napr. Nesvieti lampa č. 4...")
        
        if podnet_text:
            m_body = f"Od: {u['meno']} (VS: {u['vs']})\nEmail: {u['email']}\n\nSpráva:\n{podnet_text}"
            m_subj = f"Podnet - Victory Port - {u['meno']}"
            m_url = f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(m_subj)}&body={urllib.parse.quote(m_body)}"
            st.link_button("🚀 Odoslať cez e-mailový program", m_url, use_container_width=True)
        
        st.info(f"**Manuálne odoslanie:** Ak tlačidlo vyššie nefunguje, pošlite mail na **{MAIL_SPRAVCA}**. Do textu uveďte svoje meno ({u['meno']}) a VS ({u['vs']}).")

    # --- T2: FINANCIE (Graf + Zoznam výdavkov) ---
    with tabs[1]:
        if not df_p.empty:
            vs_p = next((c for c in df_p.columns if "VS" in c.upper()), None)
            if vs_p:
                stlpce_m = [c for c in df_p.columns if "/26" in c]
                p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
                v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Fond celkom", f"{p_sum:.2f} €")
                c2.metric("Výdavky celkom", f"{v_sum:.2f} €")
                c3.metric("Aktuálny zostatok", f"{(p_sum - v_sum):.2f} €")

                if not df_v.empty and "Dátum" in df_v.columns:
                    df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
                    v_mes = df_v.groupby(df_v["dt"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_m, fill_value=0)
                    p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                    df_g = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()})
                    st.plotly_chart(px.area(df_g, x="Mesiac", y="Zostatok", title="Vývoj financií", template="plotly_dark"), use_container_width=True)

        st.subheader("📜 Zoznam všetkých výdavkov")
        if not df_v.empty:
            st.dataframe(df_v, hide_index=True, use_container_width=True)
        else:
            st.warning("Zoznam výdavkov je nateraz prázdny.")

    # --- T3: MOJE PLATBY ---
    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_p = next((c for c in df_p.columns if "VS" in c.upper()), None)
        if vs_p:
            df_p[vs_p] = df_p[vs_p].astype(str).str.strip().str.zfill(4)
            moje = df_p[df_p[vs_p] == u['vs']]
            if not moje.empty: st.dataframe(moje, hide_index=True, use_container_width=True)
            else: st.warning("Žiadne platby pre váš VS neboli nájdené.")

    # --- T4: ANKETA ---
    with tabs[3]:
        if OTAZKA.upper() != "ŽIADNA ANKETA":
            st.subheader(f"🗳️ {OTAZKA}")
            if not df_h.empty:
                h_col = next((c for c in df_h.columns if "HLAS" in c.upper() or "ODPOVEĎ" in c.upper()), df_h.columns[-1])
                za = len(df_h[df_h[h_col].astype(str).str.upper().str.contains("ANO|ÁNO")])
                ni = len(df_h[df_h[h_col].astype(str).str.upper().str.contains("NIE")])
                
                col1, col2 = st.columns(2)
                col1.metric("ZA", f"{za} hlasov")
                col2.metric("PROTI", f"{ni} hlasov")

            st.divider()
            st.write("Odoslať hlas:")
            b1, b2 = st.columns(2)
            s_za = f"HLAS_ANO_{u['vs']}: {OTAZKA}"
            s_ni = f"HLAS_NIE_{u['vs']}: {OTAZKA}"
            b1.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(s_za)}&body=Meno: {u['meno']}", use_container_width=True)
            b2.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(s_ni)}&body=Meno: {u['meno']}", use_container_width=True)
            st.caption(f"Hlasujete ako: {u['meno']} (VS: {u['vs']})")
        else:
            st.info("Aktuálne neprebieha žiadne hlasovanie.")

except Exception as e:
    st.error(f"Vyskytla sa chyba: {e}")

st.caption("© 2026 Správa areálu Victory Port")
