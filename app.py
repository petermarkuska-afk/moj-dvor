import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
from datetime import datetime

# ==========================================
# 1. KONFIGURÁCIA PORTÁLU
# ==========================================
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Postavíme heliport?" 
HLAVNE_HESLO = "Victory2026" 
# MESACNY_PREDPIS sa už nepoužíva fixne, berie sa z hárka Konfiguracia
# TU SI ZMEŇ DÁTUM KONCA (Formát RRRR-MM-DD):
KONIEC_ANKETY = "2026-03-05"

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

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
    """
    Nová logika: Sčíta všetky predpisy z hárka Konfiguracia po aktuálny mesiac
    a odpočíta sumu všetkých stĺpcov s lomkou (napr. /26, /27) z hárka Platby.
    """
    teraz = datetime.now()
    akt_m = teraz.month
    akt_r = teraz.year

    if df_konfig.empty:
        return 0.0, 0.0, 0.0

    # 1. Suma predpisov z Konfigurácie (história + dnes)
    df_k = df_konfig.copy()
    df_k['Mesiac'] = pd.to_numeric(df_k['Mesiac'], errors='coerce')
    df_k['Rok'] = pd.to_numeric(df_k['Rok'], errors='coerce')
    df_k['Predpis'] = pd.to_numeric(df_k['Predpis'], errors='coerce').fillna(0)
    
    mask = (df_k['Rok'] < akt_r) | ((df_k['Rok'] == akt_r) & (df_k['Mesiac'] <= akt_m))
    suma_predpisov = df_k[mask]['Predpis'].sum()

    # 2. Suma všetkých platieb užívateľa (naprieč všetkými rokmi)
    vs_p = next((c for c in df_platby.columns if "VS" in c.upper()), "VS")
    df_platby[vs_p] = df_platby[vs_p].astype(str).str.strip().str.zfill(4)
    u_riadok = df_platby[df_platby[vs_p] == vs_uzivatela]

    if u_riadok.empty:
        return 0.0, suma_predpisov, -suma_predpisov

    # Vyberieme všetky stĺpce, ktoré obsahujú lomku (01/26, 05/27 atď.)
    stlpce_historie = [c for c in df_platby.columns if "/" in c]
    suma_uhrad = pd.to_numeric(u_riadok.iloc[0][stlpce_historie], errors='coerce').fillna(0).sum()

    return suma_uhrad, suma_predpisov, (suma_uhrad - suma_predpisov)

# ==========================================
# 2. AUTENTIFIKÁCIA A OVERENIE DLHU
# ==========================================
if "auth_pass" not in st.session_state: st.session_state["auth_pass"] = False
if "user_data" not in st.session_state: st.session_state["user_data"] = None
if "debt_confirmed" not in st.session_state: st.session_state["debt_confirmed"] = False

# Krok 1: Hlavné heslo
if not st.session_state["auth_pass"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte prístupové heslo:", type="password")
    if st.button("Pokračovať", use_container_width=True):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["auth_pass"] = True
            st.rerun()
        else: st.error("Nesprávne heslo!")
    st.stop()

# Krok 2: VS Identifikácia
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

# Krok 3: Kontrola nedoplatku (Interstitial)
if st.session_state["user_data"] and not st.session_state["debt_confirmed"]:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_k = get_df("Konfiguracia")
    
    if not df_p.empty and not df_k.empty:
        _, _, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
        
        if bilancia < 0:
            st.markdown(f"""
            <div style="background-color:#fff5f5; padding:30px; border-radius:15px; border:3px solid #e53e3e; text-align:center; margin-top: 50px;">
                <h2 style="color:#c53030; margin-top:0;">⚠️ Pozor</h2>
                <h3 style="color:#2d3748;">Evidujeme nedoplatok: {abs(bilancia):.2f} €</h3>
                <p style="color:#4a5568; margin-bottom: 25px;">Prosíme o vyrovnanie záväzku v čo najkratšom čase.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("") 
            if st.button("Pokračovať na web", use_container_width=True):
                st.session_state["debt_confirmed"] = True
                st.rerun()
            st.stop()
    
    st.session_state["debt_confirmed"] = True
    st.rerun()

# ==========================================
# 3. HLAVNÝ PORTÁL (Dostupný po potvrdení)
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
                    <div style="background-color:#fff3cd; padding:15px; border-radius:10px; border-left:5px solid #ffc107; margin-bottom:20px;">
                        <h4 style="color:#856404; margin-top:0;">🗳️ Prebieha hlasovanie</h4>
                        <p style="color:#856404; margin-bottom:5px;"><b>Otázka:</b> {OTAZKA}</p>
                        <p style="color:#d9534f; font-weight:bold; font-size:1.1em; margin-bottom:10px;">⌛ Koniec o: {days_left} dní</p>
                        <p style="color:#2d3748; font-style: italic; border-top: 1px solid #ffeeba; padding-top: 8px;">👉 Nezabudnite zahlasovať v ankete v záložke <b>Anketa</b>.</p>
                    </div>
                    """, unsafe_allow_html=True)
            except:
                pass

        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        st.divider()
        st.subheader("🛠️ Súkromný podnet pre správcu")
        podnet_text = st.text_area("Napíšte váš podnet (uvidí ho len správca):", key="pod_area")
        p_subj = urllib.parse.quote(f"Podnet VP {u['vs']}")
        p_body = urllib.parse.quote(f"Od: {u['meno']} (VS: {u['vs']})\nEmail: {u['email']}\n\nPodnet:\n{podnet_text}")
        st.link_button("🚀 Odoslať podnet automaticky", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)
        
        st.markdown(f"""
        <div style="background-color:#fff5f5; padding:15px; border-radius:10px; border:2px solid #e53e3e; margin-top:15px;">
            <h4 style="color:#c53030; margin-top:0;">📩 Manuálny návod</h4>
            <p style="color:#2d3748;">Pošlite e-mail na adresu: <b>{MAIL_SPRAVCA}</b><br>
            Predmet: <b>Podnet VP {u['vs']}</b><br>
            Obsah: <b>Do textu e-mailu, prosím, podrobne popíšte váš problém.</b></p>
        </div>
        """, unsafe_allow_html=True)

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

    # --- T3: MOJE PLATBY ---
    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_p = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_p] = df_p[vs_p].astype(str).str.strip().str.zfill(4)
        moje_riadky = df_p[df_p[vs_p] == u['vs']]

        if not moje_riadky.empty:
            st.dataframe(moje_riadky, hide_index=True, use_container_width=True)
            
            # NOVÝ VÝPOČET CEZ FUNKCIU
            realne, ocakavane, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)

            st.divider()
            if bilancia < 0:
                st.markdown(f"""<div style="background-color:#fff5f5; padding:20px; border-radius:12px; border:3px solid #e53e3e; text-align:center;">
                    <h3 style="color:#c53030; margin-top:0;">⚠️ Evidujeme nedoplatok: {abs(bilancia):.2f} €</h3>
                    <p style="color:#2d3748; font-size:1.1em;"><b>Historická bilancia</b></p>
                    <p style="color:#2d3748;">Suma všetkých predpisov (podľa hárka Konfiguracia): <b>{ocakavane:.2f} €</b>.</p>
                    <p style="color:#2d3748;">Suma všetkých vašich úhrad (všetky roky): <b>{realne:.2f} €</b>.</p>
                    <p style="color:#c53030; font-weight:bold;">Rozdiel: {bilancia:.2f} €</p>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div style="background-color:#f0fff4; padding:20px; border-radius:12px; border:3px solid #38a169; text-align:center;">
                    <h3 style="color:#2f855a; margin-top:0;">✅ Platby sú v poriadku</h3>
                    <p style="color:#2d3748;">Celkový kumulatívny predpis: <b>{ocakavane:.2f} €</b>.</p>
                    <p style="color:#2d3748;">Vaše celkové úhrady v systéme: <b>{realne:.2f} €</b>.</p>
                    <p style="color:#2f855a; font-weight:bold;">Máte preplatok: {bilancia:.2f} €</p>
                </div>""", unsafe_allow_html=True)

    # --- T4: ANKETA ---
    with tabs[3]:
        if OTAZKA.strip().upper() == "ŽIADNA":
            st.info("Momentálne neprebieha žiadne hlasovanie.")
        else:
            st.subheader(f"🗳️ {OTAZKA}")
            if not df_h.empty:
                c_hl = next((c for c in df_h.columns if "HLAS" in c.upper()), "Hlas")
                c_ot_all = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                df_current_h = df_h[df_h[c_ot_all].astype(str).str.strip() == OTAZKA.strip()]
                pocet_za = len(df_current_h[df_current_h[c_hl].astype(str).str.upper().str.contains("ANO|ZA")])
                pocet_proti = len(df_current_h[df_current_h[c_hl].astype(str).str.upper().str.contains("NIE|PROTI")])
                st.write("### Aktuálny stav hlasovania")
                s1, s2, s3 = st.columns(3)
                s1.metric("ZA 👍", f"{pocet_za}")
                s2.metric("PROTI 👎", f"{pocet_proti}")
                s3.metric("Spolu", f"{pocet_za + pocet_proti}")

            st.divider()
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

            st.markdown(f"""<div style="background-color:#f0fff4; padding:15px; border-radius:10px; border:2px solid #38a169; margin-top:20px;">
                <h4 style="color:#2f855a; margin-top:0;">📝 Manuálne hlasovanie</h4>
                <p style="color:#2d3748;">Pošlite e-mail na adresu: <b>{MAIL_SPRAVCA}</b><br>
                <b>Predmet ZA:</b> HLAS:ANO | VS:{u['vs']} | {OTAZKA}<br>
                <b>Predmet PROTI:</b> HLAS:NIE | VS:{u['vs']} | {OTAZKA}</p>
            </div>""", unsafe_allow_html=True)

    # --- T5: MIESTNY POKEC ---
    with tabs[4]:
        st.subheader("💬 Verejná nástenka odkazov")
        nova_sprava = st.text_area("Vaša správa pre susedov:", placeholder="Napr. Susedia, v sobotu robíme guláš...", key="pokec_area")
        if nova_sprava:
            dnes = datetime.now().strftime("%d.%m.%Y")
            o_subj = f"ODKAZ NA NASTENKU | VS:{u['vs']}"
            telo_textu = f"Datum: {dnes}\nMeno: {u['meno']}\nVS: {u['vs']}\n\nODKAZ:\n{nova_sprava}"
            o_subj_encoded = urllib.parse.quote(o_subj)
            o_body_encoded = urllib.parse.quote(telo_textu)
            mail_link = f"mailto:{MAIL_SPRAVCA}?subject={o_subj_encoded}&body={o_body_encoded}"
            st.link_button("✉️ Otvoriť e-mail s týmto textom", mail_link, use_container_width=True)
        
        st.markdown(f"""
        <div style="background-color:#f0f7ff; padding:15px; border-radius:10px; border:2px solid #007bff; margin-top:15px;">
            <h4 style="color:#0056b3; margin-top:0;">📩 Manuálny návod pre odkaz</h4>
            <p style="color:#2d3748;">Pošlite e-mail na adresu: <b>{MAIL_SPRAVCA}</b><br>
            Predmet: <b>ODKAZ NA NASTENKU | VS:{u['vs']}</b><br>
            Obsah: <b>Napíšte text, ktorý chcete zverejniť ostatným susedom.</b></p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.subheader("📌 Posledné správy")
        if not df_o.empty:
            for _, row in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{row.get('Meno', 'Neznámy')}** ({row.get('Dátum', '')})")
                    st.info(row.get('Odkaz', 'Bez textu'))
        else:
            st.info("Zatiaľ tu nie sú žiadne verejné odkazy.")

except Exception as e:
    st.error(f"Systémová informácia: {e}")

st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray; margin-top:50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
