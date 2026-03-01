import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
import io
import segno  # Knižnica pre generovanie platobných QR kódov
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURÁCIA PORTÁLU
# ==========================================
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
IBAN_FONDU = "SK0000000000000000000000"  # <--- SEM VLOŽ SKUTOČNÝ IBAN

# SEM ZADAJTE NOVÚ OTÁZKU (Ak napíšete "ŽIADNA", modul zmizne)
OTAZKA = "Súhlasíte s jednorazovým vkladom do fondu areálu?" 
# SEM ZADAJTE DÁTUM VYHLÁSENIA ANKETY (formát: RRRR-MM-DD)
DATUM_VYHLASENIA = "2026-03-01" 

HLAVNE_HESLO = "Victory2026" 
MESACNY_PREDPIS = 10.0 

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# Pomocné funkcie
def ziskaj_odpocet(start_date_str):
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        koniec_dt = start_dt + timedelta(days=10)
        teraz = datetime.now()
        zostava = koniec_dt - teraz
        return zostava, koniec_dt
    except:
        return timedelta(0), datetime.now()

def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# ==========================================
# 2. AUTENTIFIKÁCIA
# ==========================================
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
                else: st.error(f"VS {target_vs} nenájdený v adresári.")
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

    # LOGIKA ANKETY
    je_zadana_otazka = bool(OTAZKA and OTAZKA.strip() != "" and "ŽIADNA" not in OTAZKA.upper())
    anketa_aktivna = False
    dni_do_konca = 0
    koniec_dt = datetime.now()
    if je_zadana_otazka:
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
        if je_zadana_otazka and anketa_aktivna:
            st.markdown(f"""
            <div style="background-color:#fff3cd; padding:20px; border-radius:15px; border-left:8px solid #ffc107; margin-bottom:25px;">
                <h3 style="color:#856404; margin-top:0;">🗳️ Prebieha hlasovanie!</h3>
                <p style="font-size:1.1em; color:#856404; margin-bottom:10px;"><b>Otázka:</b> {OTAZKA}</p>
                <p style="font-size:1.2em; font-weight:bold; color:#d9534f; margin-bottom:10px;">⏳ Koniec o: {dni_do_konca} dní ({koniec_dt.strftime('%d.%m.%Y')})</p>
                <p style="font-size:1.0em; color:#856404;">Svoj hlas môžete odovzdať v záložke <b>Anketa</b>.</p>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        st.divider()
        st.subheader("🛠️ Súkromný podnet pre správcu")
        podnet_text = st.text_area("Napíšte váš podnet (uvidí ho len správca):", key="pod_area")
        p_subj = urllib.parse.quote(f"Podnet VP {u['vs']}")
        p_body = urllib.parse.quote(f"Od: {u['meno']} (VS: {u['vs']})\nEmail: {u['email']}\n\nPodnet:\n{podnet_text}")
        st.link_button("🚀 Odoslať podnet automaticky", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)
        
        st.markdown(f"""<div style="background-color:#fff5f5; padding:15px; border-radius:10px; border:2px solid #e53e3e; margin-top:15px;">
            <h4 style="color:#c53030; margin-top:0;">📩 Manuálny návod</h4>
            <p style="color:#2d3748;">Pošlite e-mail na adresu: <b>{MAIL_SPRAVCA}</b><br>
            Predmet: <b>Podnet VP {u['vs']}</b><br>
            Obsah: <b>Do textu e-mailu, prosím, podrobne popíšte váš problém.</b></p>
        </div>""", unsafe_allow_html=True)

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
                fig = px.area(df_g, x="Mesiac", y="Zostatok", title="Vývoj financií", template="plotly_dark")
                fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.3)')
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 Zoznam výdavkov")
        if not df_v.empty:
            show_cols = [c for c in df_v.columns if c != "temp_dt"]
            st.dataframe(df_v[show_cols], hide_index=True, use_container_width=True,
                column_config={"Doklad": st.column_config.LinkColumn("Doklad 🔗", display_text="Otvoriť")})

    # --- T3: MOJE PLATBY + QR KÓD ---
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

            st.divider()
            if bilancia < 0:
                nedoplatok = abs(bilancia)
                st.markdown(f"""<div style="background-color:#fff5f5; padding:20px; border-radius:12px; border:3px solid #e53e3e; text-align:center; margin-bottom:20px;">
                    <h3 style="color:#c53030; margin-top:0;">⚠️ Evidujeme nedoplatok: {nedoplatok:.2f} €</h3>
                    <p style="color:#2d3748;">Naskenujte QR kód pre rýchlu platbu:</p>
                </div>""", unsafe_allow_html=True)

                qr_string = f"SPD*1.0*ACC:{IBAN_FONDU}*AM:{nedoplatok:.2f}*CUR:EUR*VS:{u['vs']}*MSG:Fond Victory Port"
                qr = segno.make(qr_string)
                buff = io.BytesIO()
                qr.save(buff, kind='png', scale=10)
                
                col_q1, col_q2, col_q3 = st.columns([1, 2, 1])
                with col_q2:
                    st.image(buff.getvalue(), caption=f"QR Platba: {nedoplatok:.2f} € (VS {u['vs']})")
            else:
                st.success(f"✅ Platby sú v poriadku. Máte preplatok: {bilancia:.2f} €")

    # --- T4: ANKETA ---
    with tabs[3]:
        if not je_zadana_otazka:
            st.info("Momentálne neprebieha žiadna anketa.")
        else:
            st.subheader(f"🗳️ {OTAZKA}")
            if not df_h.empty:
                c_hl = next((c for c in df_h.columns if "HLAS" in c.upper()), "Hlas")
                c_ot_all = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                df_curr = df_h[df_h[c_ot_all].astype(str).str.strip() == OTAZKA.strip()]
                p_za = len(df_curr[df_curr[c_hl].astype(str).str.upper().str.contains("ANO|ZA")])
                p_ni = len(df_curr[df_curr[c_hl].astype(str).str.upper().str.contains("NIE|PROTI")])
                s1, s2, s3 = st.columns(3)
                s1.metric("ZA 👍", f"{p_za}")
                s2.metric("PROTI 👎", f"{p_ni}")
                s3.metric("Spolu", f"{p_za + p_ni}")

            st.divider()
            if not anketa_aktivna:
                st.error("⌛ ANKETA BOLA UZATVORENÁ (vypršal časový limit 10 dní).")
            else:
                v_cist = u['vs'].lstrip('0')
                c_vs = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
                c_ot = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                uz_hlasoval = any((df_h[c_vs].astype(str).str.strip().str.lstrip('0') == v_cist) & (df_h[c_ot].astype(str).str.strip() == OTAZKA.strip())) if not df_h.empty else False

                if uz_hlasoval:
                    st.success("✅ Váš hlas k tejto téme bol už prijatý.")
                else:
                    s_za = urllib.parse.quote(f"HLAS:ANO | VS:{u['vs']} | {OTAZKA}")
                    s_ni = urllib.parse.quote(f"HLAS:NIE | VS:{u['vs']} | {OTAZKA}")
                    b1, b2 = st.columns(2)
                    b1.link_button("👍 ZA", f"mailto:{MAIL_SPRAVCA}?subject={s_za}", use_container_width=True)
                    b2.link_button("👎 PROTI", f"mailto:{MAIL_SPRAVCA}?subject={s_ni}", use_container_width=True)

                st.markdown(f"""<div style="background-color:#f0fff4; padding:15px; border-radius:10px; border:2px solid #38a169; margin-top:20px;">
                    <h4 style="color:#2f855a; margin-top:0;">📝 Manuálne hlasovanie</h4>
                    <p style="color:#2d3748;">Pošlite e-mail na adresu: <b>{MAIL_SPRAVCA}</b><br>
                    <b>Predmet ZA:</b> HLAS:ANO | VS:{u['vs']} | {OTAZKA}<br>
                    <b>Predmet PROTI:</b> HLAS:NIE | VS:{u['vs']} | {OTAZKA}</p>
                </div>""", unsafe_allow_html=True)

            st.divider()
            st.subheader("📜 Moja história hlasovaní")
            if not df_h.empty:
                v_cist = u['vs'].lstrip('0')
                c_vs = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
                moje_h = df_h[df_h[c_vs].astype(str).str.strip().str.lstrip('0') == v_cist]
                if not moje_h.empty: st.dataframe(moje_h, hide_index=True, use_container_width=True)

    # --- T5: MIESTNY POKEC ---
    with tabs[4]:
        st.subheader("💬 Verejná nástenka odkazov")
        nova_sprava = st.text_area("Vaša správa pre susedov:", key="pokec_area")
        if nova_sprava:
            o_subj = f"ODKAZ NA NASTENKU | VS:{u['vs']}"
            t_body = f"Datum: {datetime.now().strftime('%d.%m.%Y')}\nMeno: {u['meno']}\nVS: {u['vs']}\n\nODKAZ:\n{nova_sprava}"
            st.link_button("✉️ Otvoriť e-mail", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(o_subj)}&body={urllib.parse.quote(t_body)}", use_container_width=True)
        
        st.markdown(f"""<div style="background-color:#f0fff4; padding:15px; border-radius:10px; border:2px solid #38a169; margin-top:20px;">
            <h4 style="color:#2f855a; margin-top:0;">📝 Manuálne odoslanie</h4>
            <p style="color:#2d3748;">Pošlite e-mail na adresu: <b>{MAIL_SPRAVCA}</b><br>
            <b>Predmet:</b> ODKAZ NA NÁSTENKU | VS:{u['vs']}</p>
        </div>""", unsafe_allow_html=True)

        if not df_o.empty:
            for _, row in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{row.get('Meno', 'Neznámy')}** ({row.get('Dátum', '')})")
                    st.info(row.get('Odkaz', 'Bez textu'))

except Exception as e:
    st.error(f"Systémová informácia: {e}")

st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray; margin-top:50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
