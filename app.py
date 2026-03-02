import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
from datetime import datetime
import base64

# ==========================================
# 1. KONFIGURÁCIA PORTÁLU
# ==========================================
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Postavíme heliport?" 
HLAVNE_HESLO = "Victory2026" 
KONIEC_ANKETY = "2026-03-05"

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# ==========================================
# POZADIE CEZ BASE64
# ==========================================
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img:
            return base64.b64encode(img.read()).decode()
    except:
        return ""

img_base64 = get_base64_image("image_5.png")

st.markdown(f"""
<style>
.stApp {{
    background-image: url("data:image/png;base64,{img_base64}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
section.main > div {{
    background-color: rgba(0, 0, 0, 0.92);
    padding: 30px;
    border-radius: 20px;
}}
div[data-testid="stTabs"] > div {{
    background-color: rgba(0, 0, 0, 0.92);
    border-radius: 15px;
    padding: 10px;
}}
.block-container {{
    padding-top: 2rem;
    padding-bottom: 2rem;
}}
</style>
""", unsafe_allow_html=True)

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
    Robustná logika: Sčíta všetky predpisy z Konfigurácie a SUMARIZUJE 
    všetky riadky a stĺpce s lomkou pre daný VS (rieši viacero platieb).
    """
    teraz = datetime.now()
    akt_m, akt_r = teraz.month, teraz.year

    if df_konfig.empty:
        return 0.0, 0.0, 0.0

    # 1. Suma predpisov
    df_k = df_konfig.copy()
    df_k['Mesiac'] = pd.to_numeric(df_k['Mesiac'], errors='coerce')
    df_k['Rok'] = pd.to_numeric(df_k['Rok'], errors='coerce')
    df_k['Predpis'] = pd.to_numeric(df_k['Predpis'], errors='coerce').fillna(0)
    
    mask = (df_k['Rok'] < akt_r) | ((df_k['Rok'] == akt_r) & (df_k['Mesiac'] <= akt_m))
    suma_predpisov = df_k[mask]['Predpis'].sum()

    if df_platby.empty:
        return 0.0, round(suma_predpisov, 2), round(-suma_predpisov, 2)

    # 2. Suma platieb (agregácia všetkých výskytov VS)
    vs_p = next((c for c in df_platby.columns if "VS" in c.upper() or "IDENTIFIKÁCIA" in c.upper()), "VS")
    df_platby[vs_p] = df_platby[vs_p].astype(str).str.strip().str.lstrip('0')
    target_vs = str(vs_uzivatela).strip().lstrip('0')
    
    u_riadky = df_platby[df_platby[vs_p] == target_vs]
    
    if u_riadky.empty:
        return 0.0, round(suma_predpisov, 2), round(-suma_predpisov, 2)

    stlpce_historie = [c for c in df_platby.columns if "/" in c]
    suma_uhrad = u_riadky[stlpce_historie].apply(pd.to_numeric, errors='coerce').fillna(0).values.sum()

    return round(suma_uhrad, 2), round(suma_predpisov, 2), round(suma_uhrad - suma_predpisov, 2)

# ==========================================
# 2. AUTENTIFIKÁCIA
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
            vs_col = next((c for c in df_a.columns if "VS" in c.upper()), "VS")
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
    df_p, df_k = get_df("Platby"), get_df("Konfiguracia")
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
            if st.button("Pokračovať na web", use_container_width=True):
                st.session_state["debt_confirmed"] = True
                st.rerun()
            st.stop()
    st.session_state["debt_confirmed"] = True
    st.rerun()

# ==========================================
# 3. HLAVNÝ PORTÁL
# ==========================================
try:
    u = st.session_state["user_data"]
    df_p, df_v, df_h, df_n, df_o, df_k = get_df("Platby"), get_df("Vydavky"), get_df("Hlasovanie"), get_df("Nastenka"), get_df("Odkazy"), get_df("Konfiguracia")

    st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    
    if st.button("Odhlásiť sa", use_container_width=False):
        st.session_state.update({"auth_pass": False, "user_data": None, "debt_confirmed": False})
        st.rerun()

    st.divider()
    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa", "💬 Miestny pokec"])

    with tabs[0]:
        if OTAZKA.strip().upper() != "ŽIADNA":
            try:
                target_dt = datetime.strptime(KONIEC_ANKETY, "%Y-%m-%d")
                diff = target_dt - datetime.now()
                if diff.total_seconds() > 0:
                    st.markdown(f"""
                    <div style="background-color:#ffeeba; padding:15px; border-radius:10px; border-left:5px solid #ffc107; margin-bottom:20px;">
                        <h4 style="color:#856404; margin-top:0;">🗳️ Prebieha hlasovanie</h4>
                        <p style="color:#000000; margin-bottom:5px;"><b>Otázka:</b> {OTAZKA}</p>
                        <p style="color:#bd2130; font-weight:bold; font-size:1.1em; margin-bottom:10px;">⌛ Koniec o: {diff.days + 1} dní</p>
                    </div>
                    """, unsafe_allow_html=True)
            except: pass
        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        st.divider()
        podnet_text = st.text_area("Súkromný podnet pre správcu:", key="pod_area")
        p_subj = urllib.parse.quote(f"Podnet VP {u['vs']}")
        p_body = urllib.parse.quote(f"Od: {u['meno']} (VS: {u['vs']})\n\nPodnet:\n{podnet_text}")
        st.link_button("🚀 Odoslať podnet", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)

    with tabs[1]:
        if not df_p.empty:
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).values.sum()
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
                st.plotly_chart(px.area(df_g, x="Mesiac", y="Zostatok", title="Vývoj financií", template="plotly_dark").update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.3)'), use_container_width=True)
        st.subheader("📜 Zoznam výdavkov")
        if not df_v.empty: st.dataframe(df_v, hide_index=True, use_container_width=True)

    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_p = next((c for c in df_p.columns if "VS" in c.upper() or "IDENTIFIKÁCIA" in c.upper()), "VS")
        df_p[vs_p] = df_p[vs_p].astype(str).str.strip().str.zfill(4)
        moje_riadky = df_p[df_p[vs_p] == u['vs']]
        if not moje_riadky.empty: st.dataframe(moje_riadky, hide_index=True, use_container_width=True)
        
        realne, ocakavane, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
        st.divider()
        if bilancia < 0:
            st.error(f"Nedoplatok: {abs(bilancia):.2f} € | Uhradené: {realne:.2f} € | Predpis: {ocakavane:.2f} €")
        else:
            st.success(f"Platby v poriadku. Preplatok: {bilancia:.2f} €")

        # Dynamický prehľad pre zástupcu
        df_a = get_df("Adresar")
        if not df_a.empty:
            rola_col = next((c for c in df_a.columns if "ROLA" in c.upper()), None)
            if rola_col:
                u_row = df_a[df_a[vs_p].astype(str).str.strip().str.zfill(4) == u['vs']]
                if not u_row.empty and "ZASTUPCA" in str(u_row.iloc[0][rola_col]).upper():
                    st.divider()
                    pref = u['vs'][:2]
                    st.subheader(f"📊 Prehľad bloku {pref}xx")
                    susedia_vs = [v for v in df_p[vs_p].unique() if str(v).startswith(pref)]
                    p_data = []
                    for s_vs in sorted(susedia_vs):
                        _, _, b_sus = vypocitaj_bilanciu(s_vs, df_p, df_k)
                        p_data.append({"VS": s_vs, "Stav": "Preplatok" if b_sus >= 0 else "Nedoplatok", "Suma (€)": f"{abs(b_sus):.2f}"})
                    st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)

    with tabs[3]:
        if OTAZKA.strip().upper() == "ŽIADNA": st.info("Žiadne hlasovanie.")
        else:
            st.subheader(f"🗳️ {OTAZKA}")
            if not df_h.empty:
                c_hl = next((c for c in df_h.columns if "HLAS" in c.upper()), "Hlas")
                c_ot = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                df_curr = df_h[df_h[c_ot].astype(str).str.strip() == OTAZKA.strip()]
                s1, s2 = st.columns(2)
                s1.metric("ZA 👍", len(df_curr[df_curr[c_hl].astype(str).str.upper().str.contains("ANO|ZA")]))
                s2.metric("PROTI 👎", len(df_curr[df_curr[c_hl].astype(str).str.upper().str.contains("NIE|PROTI")]))
            
            uz_hlasoval = False
            if not df_h.empty:
                uz_hlasoval = not df_h[(df_h[vs_p].astype(str).str.lstrip('0') == u['vs'].lstrip('0')) & (df_h[c_ot].astype(str).str.strip() == OTAZKA.strip())].empty
            
            if uz_hlasoval: st.success("✅ Zahlasované.")
            else:
                b1, b2 = st.columns(2)
                b1.link_button("👍 ZA", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote('HLAS:ANO | VS:'+u['vs']+' | '+OTAZKA)}", use_container_width=True)
                b2.link_button("👎 PROTI", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote('HLAS:NIE | VS:'+u['vs']+' | '+OTAZKA)}", use_container_width=True)

    with tabs[4]:
        st.subheader("💬 Verejná nástenka")
        nova_sprava = st.text_area("Vaša správa:", key="pokec_area")
        if nova_sprava:
            o_subj = urllib.parse.quote(f"ODKAZ NA NASTENKU | VS:{u['vs']}")
            o_body = urllib.parse.quote(f"Meno: {u['meno']}\n\nODKAZ:\n{nova_sprava}")
            st.link_button("✉️ Odoslať správu na zverejnenie", f"mailto:{MAIL_SPRAVCA}?subject={o_subj}&body={o_body}", use_container_width=True)
        st.divider()
        if not df_o.empty:
            for _, row in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{row.get('Meno', 'Neznámy')}** ({row.get('Dátum', '')})")
                    st.info(row.get('Odkaz', 'Bez textu'))

except Exception as e:
    st.error(f"Systémová informácia: {e}")

st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray; margin-top:50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
