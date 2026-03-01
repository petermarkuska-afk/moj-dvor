import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURÁCIA PORTÁLU
# ==========================================
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

# SEM ZADAJTE NOVÚ OTÁZKU (Ak napíšete "", modul ankety zmizne)
OTAZKA = "Súhlasíte s jednorazovým vkladom do fondu areálu?" 
# SEM ZADAJTE DÁTUM VYHLÁSENIA ANKETY (formát: RRRR-MM-DD)
DATUM_VYHLASENIA = "2026-03-01" 

HLAVNE_HESLO = "Victory2026" 
MESACNY_PREDPIS = 10.0 

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# Pomocná funkcia na výpočet zostávajúceho času
def ziskaj_odpocet(start_date_str):
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    koniec_dt = start_dt + timedelta(days=10)
    teraz = datetime.now()
    zostava = koniec_dt - teraz
    return zostava, koniec_dt

def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- AUTENTIFIKÁCIA (bezo zmeny) ---
if "auth_pass" not in st.session_state: st.session_state["auth_pass"] = False
if "user_data" not in st.session_state: st.session_state["user_data"] = None

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

# ==========================================
# 3. HLAVNÝ PORTÁL
# ==========================================
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")
    df_o = get_df("Odkazy")

    # Výpočet stavu ankety
    anketa_aktivna = False
    dni_do_konca = 0
    if OTAZKA and OTAZKA.strip() != "" and OTAZKA.upper() != "ŽIADNA":
        zostava, koniec_dt = ziskaj_odpocet(DATUM_VYHLASENIA)
        if zostava.total_seconds() > 0:
            anketa_aktivna = True
            dni_do_konca = zostava.days

    st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    
    col_out1, col_out2, col_out3 = st.columns([1,1,1])
    with col_out2:
        if st.button("Odhlásiť sa", use_container_width=True):
            st.session_state.update({"auth_pass": False, "user_data": None})
            st.rerun()

    st.divider()
    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa", "💬 Miestny pokec"])

    # --- T1: NÁSTENKA ---
    with tabs[0]:
        # NOVÝ MODUL: Upozornenie na anketu
        if anketa_aktivna:
            st.markdown(f"""
            <div style="background-color:#fff3cd; padding:20px; border-radius:15px; border-left:8px solid #ffc107; margin-bottom:25px;">
                <h3 style="color:#856404; margin-top:0;">🗳️ Prebieha hlasovanie!</h3>
                <p style="font-size:1.1em; color:#856404;"><b>Otázka:</b> {OTAZKA}</p>
                <p style="font-size:1.2em; font-weight:bold; color:#d9534f;">⏳ Koniec o: {dni_do_konca} dní ({koniec_dt.strftime('%d.%m.%Y')})</p>
                <p style="font-size:0.9em;">Svoj hlas môžete odovzdať v záložke <b>Anketa</b>.</p>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        st.divider()
        st.subheader("🛠️ Súkromný podnet pre správcu")
        podnet_text = st.text_area("Napíšte váš podnet:", key="pod_area")
        p_subj = urllib.parse.quote(f"Podnet VP {u['vs']}")
        p_body = urllib.parse.quote(f"Od: {u['meno']} (VS: {u['vs']})\nEmail: {u['email']}\n\nPodnet:\n{podnet_text}")
        st.link_button("🚀 Odoslať podnet automaticky", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)

    # --- T2 a T3 (bezo zmeny) ---
    with tabs[1]:
        if not df_p.empty:
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Fond celkom", f"{p_sum:.2f} €")
            c2.metric("Výdavky celkom", f"{v_sum:.2f} €")
            c3.metric("Zostatok", f"{(p_sum - v_sum):.2f} €")

    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_p = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_p] = df_p[vs_p].astype(str).str.strip().str.zfill(4)
        moje_platby = df_p[df_p[vs_p] == u['vs']]
        if not moje_platby.empty:
            st.dataframe(moje_platby, hide_index=True, use_container_width=True)
            t = datetime.now()
            ocakavane = t.month * MESACNY_PREDPIS
            stlpce_26 = [c for c in moje_platby.columns if "/26" in c]
            realne = pd.to_numeric(moje_platby.iloc[0][stlpce_26], errors='coerce').fillna(0).sum()
            bilancia = realne - ocakavane
            if bilancia < 0:
                st.error(f"⚠️ Evidujeme nedoplatok: {abs(bilancia):.2f} €")
            else:
                st.success(f"✅ Platby sú v poriadku. Preplatok: {bilancia:.2f} €")

    # --- T4: ANKETA (UPRAVENÁ) ---
    with tabs[3]:
        if not OTAZKA or OTAZKA.strip() == "" or OTAZKA.upper() == "ŽIADNA":
            st.info("Momentálne neprebieha žiadna anketa.")
        else:
            st.subheader(f"🗳️ {OTAZKA}")
            
            # Zobrazenie výsledkov (bezo zmeny)
            if not df_h.empty:
                c_hl = next((c for c in df_h.columns if "HLAS" in c.upper()), "Hlas")
                c_ot_all = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                df_current_h = df_h[df_h[c_ot_all].astype(str).str.strip() == OTAZKA.strip()]
                pocet_za = len(df_current_h[df_current_h[c_hl].astype(str).str.upper().str.contains("ANO|ZA")])
                pocet_proti = len(df_current_h[df_current_h[c_hl].astype(str).str.upper().str.contains("NIE|PROTI")])
                s1, s2, s3 = st.columns(3)
                s1.metric("ZA 👍", f"{pocet_za}")
                s2.metric("PROTI 👎", f"{pocet_proti}")
                s3.metric("Spolu", f"{pocet_za + pocet_proti}")

            st.divider()

            # Logika uzatvorenia tlačidiel
            if not anketa_aktivna:
                st.error("⌛ ANKETA BOLA UZATVORENÁ (vypršal časový limit 10 dní).")
            else:
                v_cist = u['vs'].lstrip('0')
                c_vs = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
                c_ot = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                uz_hlasoval = False
                if not df_h.empty and c_ot in df_h.columns:
                    mask = (df_h[c_vs].astype(str).str.strip().str.lstrip('0') == v_cist) & (df_h[c_ot].astype(str).str.strip() == OTAZKA.strip())
                    uz_hlasoval = any(mask)

                if uz_hlasoval:
                    st.success("✅ Váš hlas k tejto téme bol už prijatý.")
                else:
                    s_za = urllib.parse.quote(f"HLAS:ANO | VS:{u['vs']} | {OTAZKA}")
                    s_ni = urllib.parse.quote(f"HLAS:NIE | VS:{u['vs']} | {OTAZKA}")
                    b1, b2 = st.columns(2)
                    b1.link_button("👍 ZA", f"mailto:{MAIL_SPRAVCA}?subject={s_za}", use_container_width=True)
                    b2.link_button("👎 PROTI", f"mailto:{MAIL_SPRAVCA}?subject={s_ni}", use_container_width=True)

    # --- T5: POKEC (bezo zmeny) ---
    with tabs[4]:
        st.subheader("💬 Verejná nástenka odkazov")
        nova_sprava = st.text_area("Vaša správa pre susedov:", key="pokec_area")
        if nova_sprava:
            dnes = datetime.now().strftime("%d.%m.%Y")
            o_subj = f"ODKAZ NA NASTENKU | VS:{u['vs']}"
            telo_textu = f"Datum: {dnes}\nMeno: {u['meno']}\nVS: {u['vs']}\n\nODKAZ:\n{nova_sprava}"
            st.link_button("✉️ Otvoriť e-mail", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(o_subj)}&body={urllib.parse.quote(telo_textu)}", use_container_width=True)
        
        if not df_o.empty:
            for _, row in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{row.get('Meno', 'Neznámy')}** ({row.get('Dátum', '')})")
                    st.info(row.get('Odkaz', 'Bez textu'))

except Exception as e:
    st.error(f"Systémová informácia: {e}")

st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray; margin-top:50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
