import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
from datetime import datetime
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

# ==========================================
# 1. KONFIGURÁCIA (Načítanie zo Secrets)
# ==========================================
try:
    MAIL_SPRAVCA = st.secrets["MAIL_SPRAVCA"]
    SID = st.secrets["SID"]
    HLAVNE_HESLO = st.secrets["HLAVNE_HESLO"]
    # Predpokladám, že v secrets máte uložený aj IBAN
    IBAN = st.secrets.get("IBAN", "SK00 0000 0000 0000 0000 0000")
except Exception as e:
    st.error("⚠️ CHYBA: Chýbajú nastavenia v 'Secrets'.")
    st.stop()

OTAZKA = "ŽIADNA" 
KONIEC_ANKETY = "2026-03-05"

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# ==========================================
# POMOCNÉ FUNKCIE
# ==========================================

def generuj_pdf_potvrdenie(meno, vs, uhrady, predpis):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "Potvrdenie o platbách")
    c.setFont("Helvetica", 12)
    c.drawString(50, 780, f"Majiteľ: {meno}")
    c.drawString(50, 765, f"Variabilný symbol (VS): {vs}")
    
    c.line(50, 750, 550, 750)
    
    c.drawString(50, 720, f"Celková suma predpisov: {predpis:.2f} €")
    c.drawString(50, 705, f"Celkom uhradené: {uhrady:.2f} €")
    c.drawString(50, 690, f"Bilancia: {(uhrady - predpis):.2f} €")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 650, "Platobné údaje:")
    c.setFont("Helvetica", 12)
    c.drawString(50, 635, f"IBAN: {IBAN}")
    c.drawString(50, 620, "VS pri platbe: Použite uvedený VS")
    
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 580, "Ďakujeme za vašu príkladnú platobnú disciplínu.")
    
    c.save()
    buffer.seek(0)
    return buffer

def get_df(sheet, spreadsheet_id):
    cache_bust = int(time.time() * 1000)
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    return df.dropna(how='all')

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img:
            return base64.b64encode(img.read()).decode()
    except:
        return ""

def vypocitaj_bilanciu(vs_uzivatela, df_platby, df_konfig):
    teraz = datetime.now()
    akt_m, akt_r = teraz.month, teraz.year
    if df_konfig.empty: return 0.0, 0.0, 0.0
    
    df_k = df_konfig.copy()
    df_k['Predpis'] = pd.to_numeric(df_k['Predpis'], errors='coerce').fillna(0)
    suma_predpisov = df_k['Predpis'].sum()
    
    vs_p = next((c for c in df_platby.columns if "VS" in c.upper()), "VS")
    df_platby[vs_p] = df_platby[vs_p].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(4)
    u_riadok = df_platby[df_platby[vs_p] == vs_uzivatela]
    
    if u_riadok.empty: return 0.0, round(suma_predpisov, 2), round(-suma_predpisov, 2)
    
    stlpce_historie = [c for c in df_platby.columns if "/" in c]
    suma_uhrad = pd.to_numeric(u_riadok.iloc[0][stlpce_historie], errors='coerce').fillna(0).sum()
    return round(suma_uhrad, 2), round(suma_predpisov, 2), round(suma_uhrad - suma_predpisov, 2)

# ==========================================
# ŠTÝLOVANIE
# ==========================================
img_base64 = get_base64_image("image_5.png")
st.markdown(f"""<style>.stApp {{background-image: url("data:image/png;base64,{img_base64}"); background-size: cover;}} section.main > div {{background-color: rgba(0, 0, 0, 0.92); padding: 30px; border-radius: 20px;}}</style>""", unsafe_allow_html=True)

# ==========================================
# 2. AUTENTIFIKÁCIA
# ==========================================
if "auth_pass" not in st.session_state: st.session_state["auth_pass"] = False
if "user_data" not in st.session_state: st.session_state["user_data"] = None
if "debt_confirmed" not in st.session_state: st.session_state["debt_confirmed"] = False

if not st.session_state["auth_pass"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte prístupové heslo:", type="password")
    if st.button("Pokračovať"):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["auth_pass"] = True
            st.rerun()
    st.stop()

if st.session_state["user_data"] is None:
    st.markdown("<h2 style='text-align: center;'>🔑 Identifikácia majiteľa</h2>", unsafe_allow_html=True)
    vs_vstup = st.text_input("Variabilný symbol:")
    pin_vstup = st.text_input("PIN:", type="password")
    if st.button("Prihlásiť sa"):
        df_a = get_df("Adresar", SID)
        vs_col = next((c for c in df_a.columns if "VS" in c.upper()), None)
        pin_col = next((c for c in df_a.columns if "PIN" in c.upper()), None)
        df_a[vs_col] = df_a[vs_col].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
        user_row = df_a[(df_a[vs_col] == vs_vstup.zfill(4)) & (df_a[pin_col].astype(str) == pin_vstup)]
        if not user_row.empty:
            st.session_state["user_data"] = {"vs": vs_vstup.zfill(4), "meno": str(user_row.iloc[0].get("Meno a priezvisko", "Neznámy")), "email": str(user_row.iloc[0].get("Email", "")), "rola": str(user_row.iloc[0].get("ROLA", "")).upper(), "je_spravca": str(user_row.iloc[0].get("SPRAVCA", "")).upper() == "ANO"}
            st.rerun()
    st.stop()

# ==========================================
# 3. HLAVNÝ PORTÁL
# ==========================================
u = st.session_state["user_data"]
df_p = get_df("Platby", SID)
df_v = get_df("Vydavky", SID)
df_h = get_df("Hlasovanie", SID)
df_n = get_df("Nastenka", SID)
df_o = get_df("Odkazy", SID)
df_k = get_df("Konfiguracia", SID)
df_a = get_df("Adresar", SID)

st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa", "💬 Miestny pokec"])

# --- TAB 2: MOJE PLATBY ---
with tabs[2]:
    st.subheader(f"💰 Moje platby (VS: {u['vs']})")
    realne, predpis, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
    
    st.dataframe(df_p[df_p[next((c for c in df_p.columns if "VS" in c.upper()), "VS")] == u['vs']], hide_index=True, use_container_width=True)
    
    # Tlačidlo na stiahnutie PDF
    pdf_data = generuj_pdf_potvrdenie(u['meno'], u['vs'], realne, predpis)
    st.download_button(
        label="📥 Stiahnuť potvrdenie o platbách (PDF)",
        data=pdf_data,
        file_name=f"Potvrdenie_VS_{u['vs']}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    # --- T1: NÁSTENKA ---
    with tabs[0]:
        if OTAZKA.strip().upper() != "ŽIADNA":
            try:
                target_dt = datetime.strptime(KONIEC_ANKETY, "%Y-%m-%d")
                diff = target_dt - datetime.now()
                days_left = diff.days + 1
                if diff.total_seconds() > 0:
                    st.markdown(f"""
                    <div style="background-color:#ffeeba; padding:15px; border-radius:10px; border-left:5px solid #ffc107; margin-bottom:20px;">
                        <h4 style="color:#856404; margin-top:0;">🗳️ Prebieha hlasovanie</h4>
                        <p style="color:#2d3748; margin-bottom:5px;"><b>Otázka:</b> {OTAZKA}</p>
                        <p style="color:#bd2130; font-weight:bold; font-size:1.1em; margin-bottom:10px;">⌛ Koniec o: {days_left} dní</p>
                        <p style="color:#2d3748; font-style: italic; border-top: 1px solid #dfc27d; padding-top: 8px;">👉 Nezabudnite zahlasovať v ankete v záložke <b>Anketa</b>.</p>
                    </div>
                    """, unsafe_allow_html=True)
            except: pass

        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty:
            # Filtrujeme stĺpce, ktoré nie sú prázdne (odstraňujeme Unnamed z Excelu)
            relevantne_stlpce = [c for c in df_n.columns if "Unnamed" not in str(c)]
            # Zobrazenie pomocou dataframe pre podporu skrytia indexu a scrollovania
            st.dataframe(
                df_n[relevantne_stlpce].iloc[::-1], 
                hide_index=True, 
                use_container_width=True,
                height=250 # Výška pre cca 7 záznamov so scrollbarom
            )
            
        st.divider()
        st.subheader("🛠️ Súkromný podnet pre správcu")
        podnet_text = st.text_area("Napíšte váš podnet (uvidí ho len správca):", key="pod_area")
        p_subj = urllib.parse.quote(f"Podnet VP {u['vs']}")
        p_body = urllib.parse.quote(f"Od: {u['meno']} (VS: {u['vs']})\nEmail: {u['email']}\n\nPodnet:\n{podnet_text}")
        st.link_button("🚀 Odoslať podnet", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)
        
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
            vsetky_m = [c for c in df_p.columns if "/" in c]
            teraz = datetime.now()
            stlpce_m = []
            for c in vsetky_m:
                try:
                    if datetime.strptime(c, "%m/%y") <= teraz: stlpce_m.append(c)
                except: continue
            stlpce_m.sort(key=lambda x: datetime.strptime(x, "%m/%y"))

            if stlpce_m:
                p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
                v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
                c1, c2, c3 = st.columns(3)
                c1.metric("Fond celkom", f"{p_sum:.2f} €")
                c2.metric("Výdavky celkom", f"{v_sum:.2f} €")
                c3.metric("Zostatok", f"{(p_sum - v_sum):.2f} €")

                if not df_v.empty:
                    df_v_graph = df_v.copy()
                    df_v_graph["temp_dt"] = pd.to_datetime(df_v_graph["Dátum"], dayfirst=True, errors='coerce')
                    v_mes = df_v_graph.groupby(df_v_graph["temp_dt"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_m, fill_value=0)
                    p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                    df_g = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()})
                    fig = px.area(df_g, x="Mesiac", y="Zostatok", title="Vývoj financií (k dnešnému dňu)", template="plotly_dark")
                    fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.3)')
                    st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 Zoznam výdavkov")
        if not df_v.empty:
            st.dataframe(df_v, hide_index=True, use_container_width=True,
                column_config={"Doklad": st.column_config.LinkColumn("Doklad 🔗", display_text="Otvoriť")})

    # --- T3: MOJE PLATBY ---
    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_p = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_p] = df_p[vs_p].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
        moje_riadky = df_p[df_p[vs_p] == u['vs']]

        if not moje_riadky.empty:
            st.dataframe(moje_riadky, hide_index=True, use_container_width=True)
            realne, ocakavane, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)

            st.divider()
            if bilancia < 0:
                st.markdown(f"""<div style="background-color:#fff5f5; padding:20px; border-radius:12px; border:3px solid #e53e3e; text-align:center;">
                    <h3 style="color:#c53030; margin-top:0;">⚠️ Evidujeme nedoplatok: {abs(bilancia):.2f} €</h3>
                    <p style="color:#2d3748;">Suma všetkých predpisov: <b>{ocakavane:.2f} €</b> | Suma vašich úhrad: <b>{realne:.2f} €</b></p>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div style="background-color:#f0fff4; padding:20px; border-radius:12px; border:3px solid #38a169; text-align:center;">
                    <h3 style="color:#2f855a; margin-top:0;">✅ Platby sú v poriadku</h3>
                    <p style="color:#2d3748;">Suma predpisov: <b>{ocakavane:.2f} €</b> | Vaše úhrady: <b>{realne:.2f} €</b> | Preplatok: <b>{bilancia:.2f} €</b></p>
                </div>""", unsafe_allow_html=True)

        # PREHĽAD ZÁSTUPCU
        je_zastupca_v_tabulke = False
        if not df_a.empty:
            vs_col_a = next((c for c in df_a.columns if "VS" in c.upper()), "VS")
            rola_col = next((c for c in df_a.columns if "ROLA" in c.upper()), None)
            if rola_col:
                u_row = df_a[df_a[vs_col_a].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4) == u['vs']]
                if not u_row.empty and "ZASTUPCA" in str(u_row.iloc[0][rola_col]).upper():
                    je_zastupca_v_tabulke = True

        if je_zastupca_v_tabulke:
            st.divider()
            pref = u['vs'][:2]
            st.subheader(f"📊 Prehľad susedov (Blok {pref}xx)")
            susedia_vs = [v for v in df_p[vs_p].unique() if str(v).startswith(pref)]
            p_data = []
            for s_vs in sorted(susedia_vs):
                _, _, b_sus = vypocitaj_bilanciu(s_vs, df_p, df_k)
                p_data.append({"VS": s_vs, "Stav": "Preplatok" if b_sus >= 0 else "Nedoplatok", "Suma (€)": f"{abs(b_sus):.2f}"})
            df_blok = pd.DataFrame(p_data)
            def styluj_stav(row):
                bg = 'background-color: #441111; color: white;' if row['Stav'] == 'Nedoplatok' else 'background-color: #114411; color: white;'
                return [bg] * len(row)
            st.dataframe(df_blok.style.apply(styluj_stav, axis=1), hide_index=True, use_container_width=True)

    # --- T4: ANKETA ---
    with tabs[3]:
        if OTAZKA.strip().upper() == "ŽIADNA":
            st.info("Momentálne neprebieha žiadne hlasovanie.")
        else:
            st.subheader(f"🗳️ {OTAZKA}")
            if not df_h.empty:
                c_hl = next((c for c in df_h.columns if "HLAS" in c.upper()), "Hlas")
                c_ot_all = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                df_curr = df_h[df_h[c_ot_all].astype(str).str.strip() == OTAZKA.strip()]
                pocet_za = len(df_curr[df_curr[c_hl].astype(str).str.upper().str.contains("ANO|ZA")])
                pocet_pro = len(df_curr[df_curr[c_hl].astype(str).str.upper().str.contains("NIE|PROTI")])
                s1, s2, s3 = st.columns(3)
                s1.metric("ZA 👍", f"{pocet_za}")
                s2.metric("PROTI 👎", f"{pocet_pro}")
                s3.metric("Spolu", f"{pocet_za + pocet_pro}")

            st.divider()
            v_cist = u['vs'].lstrip('0')
            c_vs_h = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
            c_ot_h = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
            uz_hlasoval = False
            if not df_h.empty and c_ot_h in df_h.columns:
                mask = (df_h[c_vs_h].astype(str).str.strip().str.lstrip('0') == v_cist) & (df_h[c_ot_h].astype(str).str.strip() == OTAZKA.strip())
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
        
        st.divider()
        st.subheader("📜 História mojich hlasovaní")
        if not df_h.empty:
            c_vs_hist = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
            df_h[c_vs_hist] = df_h[c_vs_hist].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(4)
            moje_h = df_h[df_h[c_vs_hist] == u['vs']]
            if not moje_h.empty:
                st.dataframe(moje_h, hide_index=True, use_container_width=True)
            else: st.info("Zatiaľ ste nehlasovali.")

    # --- T5: MIESTNY POKEC ---
    with tabs[4]:
        st.subheader("💬 Verejná nástenka odkazov")
        nova_sprava = st.text_area("Vaša správa pre susedov:", placeholder="Napr. Susedia, v sobotu robíme guláš...", key="pokec_area")
        if nova_sprava:
            o_subj = urllib.parse.quote(f"ODKAZ NA NASTENKU | VS:{u['vs']}")
            o_body = urllib.parse.quote(f"Od: {u['meno']}\n\nOdkaz:\n{nova_sprava}")
            st.link_button("✉️ Otvoriť e-mail s týmto textom", f"mailto:{MAIL_SPRAVCA}?subject={o_subj}&body={o_body}", use_container_width=True)
        st.markdown(f"""<div style="background-color:#f0f7ff; padding:15px; border-radius:10px; border:2px solid #007bff; margin-top:15px;">
            <h4 style="color:#0056b3; margin-top:0;">📩 Manuálny návod</h4>
            <p style="color:#2d3748;">Pošlite e-mail na <b>{MAIL_SPRAVCA}</b> s predmetom <b>ODKAZ NA NASTENKU | VS:{u['vs']}</b></p>
        </div>""", unsafe_allow_html=True)
        st.divider()
        if not df_o.empty:
            for _, row in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{row.get('Meno', 'Neznámy')}** ({row.get('Dátum', '')})")
                    st.info(row.get('Odkaz', 'Bez textu'))

    # --- T6: SPRÁVA (HLAVNÝ KOMUNIKÁTOR) ---
    if u["je_spravca"] or u["rola"] == "ZASTUPCA":
        with tabs[-1]:
            st.subheader("⚙️ Administrácia a komunikácia")
            vs_col_a = next((c for c in df_a.columns if "VS" in c.upper()), "VS")
            df_a[vs_col_a] = df_a[vs_col_a].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
            
            if u["je_spravca"]:
                df_ciel = df_a.copy()
            else:
                prefix = u["vs"][:2]
                df_ciel = df_a[df_a[vs_col_a].str.startswith(prefix)]

            st.write("### ✍️ Napísať hromadný e-mail")
            user_subj = st.text_input("Predmet e-mailu:")
            user_msg = st.text_area("Text e-mailu:")
            
            email_col = next((c for c in df_ciel.columns if "EMAIL" in c.upper()), "Email")
            maily = [str(m) for m in df_ciel[email_col].dropna().unique().tolist() if "@" in str(m)]
            
            if maily:
                bcc_all = "; ".join(maily)
                st.link_button(f"✉️ Odoslať e-mail ({len(maily)} susedom)", f"mailto:?bcc={bcc_all}&subject={urllib.parse.quote(user_subj)}&body={urllib.parse.quote(user_msg)}", use_container_width=True)

except Exception as e:
    if st.session_state["user_data"] is not None:
        st.error(f"Systémová informácia: {e}")

st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray; margin-top:50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)

