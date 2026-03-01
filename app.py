import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
import os
import base64
from datetime import datetime

# ==========================================
# 1. VIZUÁLNY MODUL (POZADIE A DIZAJN)
# ==========================================
st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

def apply_victory_design():
    # Získanie cesty k obrázku v rovnakom priečinku ako skript
    script_directory = os.path.dirname(__file__)
    img_path = os.path.join(script_directory, "image_5.png")
    
    img_base64 = ""
    # Pokus o načítanie obrázka
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()
    
    # CSS pre plávajúci panel a pozadie areálu
    st.markdown(f"""
        <style>
        /* Pozadie celej aplikácie s obrázkom */
        .stApp {{
            background-image: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), 
                              url("data:image/png;base64,{img_base64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* Stredový panel (Main Content Area) - Čierny a čitateľný */
        .main .block-container {{
            background-color: #0e1117 !important;
            max-width: 850px !important;
            padding: 40px !important;
            margin: 50px auto !important;
            border-radius: 20px;
            box-shadow: 0 10px 50px rgba(0,0,0,1);
            color: white !important;
        }}

        /* Vynútenie bieleho textu pre všetko v strede */
        h1, h2, h3, h4, p, span, label, li {{
            color: white !important;
        }}

        /* Úprava tabuliek aby boli čitateľné na čiernom */
        .stDataFrame, .stTable {{
            background-color: rgba(255,255,255,0.05) !important;
            border-radius: 10px;
        }}
        
        /* Oprava farby textu v tabuľkách */
        [data-testid="stTable"] td, [data-testid="stTable"] th {{
            color: white !important;
        }}

        /* Skrytie horného panelu Streamlitu */
        header {{
            visibility: hidden;
        }}
        </style>
    """, unsafe_allow_html=True)

# Aktivácia dizajnu
apply_victory_design()

# ==========================================
# 2. KONFIGURÁCIA A NAČÍTANIE DÁT
# ==========================================
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Postavíme heliport?" 
HLAVNE_HESLO = "Victory2026" 
ZASTUPCOVIA = ["1007", "1105", "1201"] 
KONIEC_ANKETY = "2026-03-05"

def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

def vypocitaj_bilanciu(vs_uzivatela, df_platby, df_konfig):
    teraz = datetime.now()
    akt_m = teraz.month
    akt_r = teraz.year
    if df_konfig.empty: return 0.0, 0.0, 0.0
    df_k = df_konfig.copy()
    df_k['Mesiac'] = pd.to_numeric(df_k['Mesiac'], errors='coerce')
    df_k['Rok'] = pd.to_numeric(df_k['Rok'], errors='coerce')
    df_k['Predpis'] = pd.to_numeric(df_k['Predpis'], errors='coerce').fillna(0)
    mask = (df_k['Rok'] < akt_r) | ((df_k['Rok'] == akt_r) & (df_k['Mesiac'] <= akt_m))
    suma_predpisov = df_k[mask]['Predpis'].sum()
    vs_p = next((c for c in df_platby.columns if "VS" in c.upper()), "VS")
    df_platby[vs_p] = df_platby[vs_p].astype(str).str.strip().str.zfill(4)
    u_riadok = df_platby[df_platby[vs_p] == vs_uzivatela]
    if u_riadok.empty: return 0.0, round(suma_predpisov, 2), round(-suma_predpisov, 2)
    stlpce_historie = [c for c in df_platby.columns if "/" in c]
    suma_uhrad = pd.to_numeric(u_riadok.iloc[0][stlpce_historie], errors='coerce').fillna(0).sum()
    return round(suma_uhrad, 2), round(suma_predpisov, 2), round(suma_uhrad - suma_predpisov, 2)

# ==========================================
# 3. AUTENTIFIKÁCIA
# ==========================================
if "auth_pass" not in st.session_state: st.session_state["auth_pass"] = False
if "user_data" not in st.session_state: st.session_state["user_data"] = None
if "debt_confirmed" not in st.session_state: st.session_state["debt_confirmed"] = False

if not st.session_state["auth_pass"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte prístupové heslo:", type="password")
    if st.button("Pokračovať", use_container_width=True):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["auth_pass"] = True
            st.rerun()
        else: st.error("Nesprávne heslo!")
    st.stop()

if st.session_state["auth_pass"] and st.session_state["user_data"] is None:
    st.markdown("<h2 style='text-align: center;'>🔑 Identifikácia majiteľa</h2>", unsafe_allow_html=True)
    vs_vstup = st.text_input("Zadajte váš Variabilný symbol (VS):", placeholder="Napr. 1007")
    if st.button("Prihlásiť sa", use_container_width=True):
        df_a = get_df("Adresar")
        if not df_a.empty:
            vs_col = next((c for c in df_a.columns if "VS" in c.upper()), None)
            if vs_col:
                df_a[vs_col] = df_a[vs_col].astype(str).str.strip().str.zfill(4)
                target_vs = vs_vstup.strip().zfill(4)
                user_row = df_a[df_a[vs_col] == target_vs]
                if not user_row.empty:
                    st.session_state["user_data"] = {
                        "vs": target_vs,
                        "meno": str(user_row.iloc[0].get("Meno a priezvisko", "Neznámy")),
                        "email": str(user_row.iloc[0].get("Email", "Neuvedený"))
                    }
                    st.rerun()
                else: st.error(f"VS {target_vs} nenájdený.")
    st.stop()

if st.session_state["user_data"] and not st.session_state["debt_confirmed"]:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_k = get_df("Konfiguracia")
    if not df_p.empty and not df_k.empty:
        _, _, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
        if bilancia < 0:
            st.markdown(f"""
            <div style="background-color:#c53030; padding:30px; border-radius:15px; border:3px solid #ffffff; text-align:center; margin-top: 50px;">
                <h2 style="color:white; margin-top:0;">⚠️ Pozor</h2>
                <h3 style="color:white;">Evidujeme nedoplatok: {abs(bilancia):.2f} €</h3>
                <p style="color:white; margin-bottom: 25px;">Prosíme o vyrovnanie záväzku v čo najkratšom čase.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Pokračovať na web", use_container_width=True):
                st.session_state["debt_confirmed"] = True
                st.rerun()
            st.stop()
    st.session_state["debt_confirmed"] = True
    st.rerun()

# ==========================================
# 4. HLAVNÝ OBSAH (V PANELI)
# ==========================================
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")
    df_o = get_df("Odkazy")
    df_k = get_df("Konfiguracia")

    st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    
    col_out1, col_out2, col_out3 = st.columns([1,1,1])
    with col_out2:
        if st.button("Odhlásiť sa", use_container_width=True):
            st.session_state.update({"auth_pass": False, "user_data": None, "debt_confirmed": False})
            st.rerun()

    st.divider()
    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa", "💬 Miestny pokec"])

    # --- T1: NÁSTENKA ---
    with tabs[0]:
        if OTAZKA.strip().upper() != "ŽIADNA":
            try:
                target_dt = datetime.strptime(KONIEC_ANKETY, "%Y-%m-%d")
                diff = target_dt - datetime.now()
                days_left = diff.days + 1
                if diff.total_seconds() > 0:
                    st.markdown(f"""
                    <div style="background-color:rgba(255,238,186,0.1); padding:15px; border-radius:10px; border-left:5px solid #ffc107; margin-bottom:20px;">
                        <h4 style="color:#ffc107; margin-top:0;">🗳️ Prebieha hlasovanie</h4>
                        <p style="color:white; margin-bottom:5px;"><b>Otázka:</b> {OTAZKA}</p>
                        <p style="color:#ff4b4b; font-weight:bold; font-size:1.1em; margin-bottom:10px;">⌛ Koniec o: {days_left} dní</p>
                    </div>
                    """, unsafe_allow_html=True)
            except: pass
        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        st.divider()
        st.subheader("🛠️ Súkromný podnet")
        podnet_text = st.text_area("Napíšte váš podnet:", key="pod_area")
        p_subj = urllib.parse.quote(f"Podnet VP {u['vs']}")
        p_body = urllib.parse.quote(f"Od: {u['meno']} (VS: {u['vs']})\n\n{podnet_text}")
        st.link_button("🚀 Odoslať podnet", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)

    # --- T2: FINANCIE ---
    with tabs[1]:
        if not df_p.empty:
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Fond celkom", f"{p_sum:.2f} €")
            c2.metric("Výdavky celkom", f"{v_sum:.2f} €")
            c3.metric("Zostatok", f"{(p_sum - v_sum):.2f} €")
            if not df_v.empty and "Dátum" in df_v.columns:
                df_v_graph = df_v.copy()
                df_v_graph["temp_dt"] = pd.to_datetime(df_v_graph["Dátum"], dayfirst=True, errors='coerce')
                v_mes = df_v_graph.groupby(df_v_graph["temp_dt"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_m, fill_value=0)
                p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                df_g = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()})
                fig = px.area(df_g, x="Mesiac", y="Zostatok", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        st.subheader("📜 Zoznam výdavkov")
        if not df_v.empty:
            st.dataframe(df_v, hide_index=True, use_container_width=True)

    # --- T3: MOJE PLATBY ---
    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_p = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_p] = df_p[vs_p].astype(str).str.strip().str.zfill(4)
        moje_riadky = df_p[df_p[vs_p] == u['vs']]
        if not moje_riadky.empty:
            st.dataframe(moje_riadky, hide_index=True, use_container_width=True)
            realne, ocakavane, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
            st.divider()
            if bilancia < 0:
                st.error(f"⚠️ Evidujeme nedoplatok: {abs(bilancia):.2f} €")
            else:
                st.success(f"✅ Platby sú v poriadku. Preplatok: {bilancia:.2f} €")

        # Dynamická kontrola zástupcu
        je_zastupca_v_tabulke = False
        df_a = get_df("Adresar")
        if not df_a.empty:
            vs_col_a = next((c for c in df_a.columns if "VS" in c.upper()), "VS")
            rola_col = next((c for c in df_a.columns if "ROLA" in c.upper()), None)
            if rola_col:
                u_row = df_a[df_a[vs_col_a].astype(str).str.strip().str.zfill(4) == u['vs']]
                if not u_row.empty and "ZASTUPCA" in str(u_row.iloc[0][rola_col]).upper():
                    je_zastupca_v_tabulke = True
        if je_zastupca_v_tabulke:
            st.divider()
            pref = u['vs'][:2]
            st.subheader(f"📊 Prehľad bloku {pref}xx")
            susedia_vs = [v for v in df_p[vs_p].unique() if str(v).startswith(pref)]
            p_data = []
            for s_vs in sorted(susedia_vs):
                _, _, b_sus = vypocitaj_bilanciu(s_vs, df_p, df_k)
                p_data.append({"VS": s_vs, "Stav": "Preplatok" if b_sus >= 0 else "Nedoplatok", "Suma (€)": f"{abs(b_sus):.2f}"})
            st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)

    # --- T4: ANKETA ---
    with tabs[3]:
        if OTAZKA.strip().upper() == "ŽIADNA":
            st.info("Žiadne aktívne hlasovanie.")
        else:
            st.subheader(f"🗳️ {OTAZKA}")
            if not df_h.empty:
                c_hl = next((c for c in df_h.columns if "HLAS" in c.upper()), "Hlas")
                c_ot_all = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                df_curr = df_h[df_h[c_ot_all].astype(str).str.strip() == OTAZKA.strip()]
                za = len(df_curr[df_curr[c_hl].astype(str).str.upper().str.contains("ANO|ZA")])
                proti = len(df_curr[df_curr[c_hl].astype(str).str.upper().str.contains("NIE|PROTI")])
                s1, s2 = st.columns(2)
                s1.metric("ZA 👍", za)
                s2.metric("PROTI 👎", proti)
            st.divider()
            s_za = urllib.parse.quote(f"HLAS:ANO | VS:{u['vs']} | {OTAZKA}")
            s_ni = urllib.parse.quote(f"HLAS:NIE | VS:{u['vs']} | {OTAZKA}")
            b1, b2 = st.columns(2)
            b1.link_button("👍 ZA", f"mailto:{MAIL_SPRAVCA}?subject={s_za}", use_container_width=True)
            b2.link_button("👎 PROTI", f"mailto:{MAIL_SPRAVCA}?subject={s_ni}", use_container_width=True)

    # --- T5: POKEC ---
    with tabs[4]:
        st.subheader("💬 Verejná nástenka")
        msg = st.text_area("Vaša správa:", placeholder="Napíšte odkaz susedom...", key="pokec_area")
        if msg:
            o_subj = urllib.parse.quote(f"ODKAZ NA NASTENKU | VS:{u['vs']}")
            o_body = urllib.parse.quote(f"VS: {u['vs']}\n\n{msg}")
            st.link_button("✉️ Odoslať odkaz", f"mailto:{MAIL_SPRAVCA}?subject={o_subj}&body={o_body}", use_container_width=True)
        st.divider()
        if not df_o.empty:
            for _, row in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{row.get('Meno', 'Neznámy')}**")
                    st.info(row.get('Odkaz', '...'))

except Exception as e:
    st.error(f"Systémová informácia: {e}")

st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray; margin-top:50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
