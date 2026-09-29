import json
import os
import sqlite3
import subprocess
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Job Matcher - Control Center", page_icon="⚙️", layout="wide")

CONFIG_FILE = "config_params.json"
MESSAGES_FILE = "messages.json"
DB_NAME = "jobs.db"

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

st.sidebar.title("🎛️ Navigation")
page = st.sidebar.radio("Aller vers", ["💼 Dashboard des Offres", "⚙️ Profil & Critères", "💬 Messages", "🚀 Actions & Scripts"])

# ==========================================
# PAGE 1 : DASHBOARD DES OFFRES
# ==========================================
if page == "💼 Dashboard des Offres":
    st.title("💼 Offres d'Emploi Sélectionnées")

    if not os.path.exists(DB_NAME):
        st.warning(f"La base de données `{DB_NAME}` n'existe pas encore.")
    else:
        conn = sqlite3.connect(DB_NAME)

        st.sidebar.header("Filtres d'affichage")
        min_score = st.sidebar.slider("Score de correspondance minimal", 0, 100, 50, 5)

        selected_sites = st.sidebar.multiselect(
            "Plateformes d'origine", 
            ["linkedin", "indeed", "google", "welcometothejungle", "welovedevs", "apec", "france_travail"],
            default=["linkedin", "indeed", "google", "welcometothejungle", "welovedevs", "apec", "france_travail"]
        )

        query = """
            SELECT title, company, location, site, ai_score, ai_analysis, job_url, date_posted, status
            FROM jobs
            WHERE ai_score >= ? AND status != 'rejected'
            ORDER BY ai_score DESC
        """
        df = pd.read_sql_query(query, conn, params=(min_score,))
        conn.close()

        if selected_sites and not df.empty:
            df = df[df["site"].isin(selected_sites)]

        st.subheader(f"🎯 {len(df)} offre(s) retenue(s) (Score ≥ {min_score})")

        for idx, row in df.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### [{row['title']}]({row['job_url']})")
                    st.caption(f"🏢 **{row['company']}** | 📍 **{row['location']}** | 🌐 {row['site'].upper()} | 📅 {row['date_posted']}")
                
                with col2:
                    st.metric(label="Score Match", value=f"{row['ai_score']} / 100")

                if row['ai_analysis']:
                    try:
                        analysis = json.loads(row['ai_analysis'])
                        
                        # Affichage générique des compétences / mots-clés
                        keywords = analysis.get("competences_cles") or analysis.get("tags", [])
                        if keywords:
                            badges_html = " ".join([f"<span style='background-color: #2b303c; color: #4CAF50; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;'>{kw}</span>" for kw in keywords])
                            st.markdown(f"**Compétences / Mots-clés :** {badges_html}", unsafe_allow_html=True)
                            st.write("")

                        st.markdown(f"**Explication :** {analysis.get('explication', '')}")
                        
                        p_col1, p_col2 = st.columns(2)
                        with p_col1:
                            if analysis.get('points_forts'):
                                st.markdown("✅ **Points forts :**")
                                for pf in analysis['points_forts']:
                                    st.markdown(f"- {pf}")
                        with p_col2:
                            if analysis.get('points_faibles'):
                                st.markdown("⚠️ **Points d'attention :**")
                                for pf in analysis['points_faibles']:
                                    st.markdown(f"- {pf}")
                    except Exception:
                        st.text(row['ai_analysis'])
                        
                st.divider()

# ==========================================
# PAGE 2 : PROFIL ET CRITÈRES DE RECHERCHE
# ==========================================
elif page == "⚙️ Profil & Critères":
    st.title("⚙️ Profil Recherché & Critères de Tri")

    config_data = load_json(CONFIG_FILE)

    with st.form("config_form"):
        st.subheader("👤 Profil de la personne")
        intitule_poste = st.text_input("Intitulé du poste recherché", value=config_data.get("profile", {}).get("intitule_poste", "Secrétaire Administrative"))
        competences_recherchees = st.text_area("Compétences / Domaines recherchés", value=config_data.get("profile", {}).get("competences_recherchees", "Accueil, Secrétariat, Bureautique, Organisation"))

        st.subheader("📍 Localisations autorisées")
        locations_str = st.text_area(
            "Mots-clés de localisation acceptés (séparés par des virgules)", 
            value=", ".join(config_data.get("filtering", {}).get("allowed_locations", []))
        )

        st.subheader("🚫 Mots-clés / Critères Exclus")
        excluded_terms_str = st.text_area(
            "Termes ou critères de rejet automatique (ex: Nuit, Commercial, Stage, etc.)", 
            value=", ".join(config_data.get("filtering", {}).get("excluded_terms", []))
        )

        st.subheader("🤖 Modèle IA & Prompt")
        model_name = st.text_input("Modèle Ollama", value=config_data.get("ollama", {}).get("model_name", "gemma2"))
        prompt_text = st.text_area(
            "Template du Prompt IA", 
            value=config_data.get("prompt_templates", {}).get("evaluation_prompt", ""),
            height=250
        )

        submitted = st.form_submit_button("💾 Enregistrer la configuration")
        if submitted:
            new_config = {
                "database": {"db_name": config_data.get("database", {}).get("db_name", "jobs.db")},
                "ollama": {
                    "model_name": model_name,
                    "temperature": config_data.get("ollama", {}).get("temperature", 0.1),
                    "repeat_penalty": config_data.get("ollama", {}).get("repeat_penalty", 1.2)
                },
                "profile": {
                    "intitule_poste": intitule_poste,
                    "competences_recherchees": competences_recherchees
                },
                "filtering": {
                    "allowed_locations": [x.strip() for x in locations_str.split(",") if x.strip()],
                    "excluded_terms": [x.strip() for x in excluded_terms_str.split(",") if x.strip()]
                },
                "prompt_templates": {
                    "evaluation_prompt": prompt_text
                }
            }
            save_json(CONFIG_FILE, new_config)
            st.success("Profil et critères sauvegardés avec succès !")

# ==========================================
# PAGE 3 : MESSAGES ET TEXTES
# ==========================================
elif page == "💬 Messages":
    st.title("💬 Personnalisation des textes (`messages.json`)")
    messages_data = load_json(MESSAGES_FILE)
    json_str = st.text_area("Structure JSON des messages", value=json.dumps(messages_data, ensure_ascii=False, indent=2), height=400)

    if st.button("💾 Enregistrer les messages"):
        try:
            parsed_json = json.loads(json_str)
            save_json(MESSAGES_FILE, parsed_json)
            st.success("Messages sauvegardés avec succès !")
        except Exception as e:
            st.error(f"Erreur de format JSON : {e}")

# ==========================================
# PAGE 4 : LANCEMENT DES SCRIPTS
# ==========================================
elif page == "🚀 Actions & Scripts":
    st.title("🚀 Lancement des traitements")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Tri Express (Mots-Clés & Lieu)")
        st.write("Filtre instantanément par **Lieu** et **Mots-clés exclus** (sans LLM).")
        if st.button("⚡ Exécuter le tri express (`re_filter.py`)"):
            with st.spinner("Exécution..."):
                try:
                    result = subprocess.run(
                        ["python", "re_filter.py"], 
                        capture_output=True, 
                        text=True, 
                        encoding="utf-8", 
                        errors="replace",
                        env=env,
                        check=True
                    )
                    st.success("Tri express terminé !")
                    st.code(result.stdout)
                except subprocess.CalledProcessError as e:
                    st.error(f"Erreur lors de l'exécution : {e.stderr}")

    with col2:
        st.subheader("2. Évaluation IA par Profil")
        st.write("Évalue chaque offre par rapport au profil défini dans l'onglet **Profil & Critères**.")
        if st.button("🧠 Lancer l'évaluation IA (`ai_matcher.py`)"):
            with st.spinner("Analyse par l'IA en cours..."):
                try:
                    result = subprocess.run(
                        ["python", "ai_matcher.py"], 
                        capture_output=True, 
                        text=True, 
                        encoding="utf-8", 
                        errors="replace",
                        env=env,
                        check=True
                    )
                    st.success("Évaluation IA terminée !")
                    st.code(result.stdout)
                except subprocess.CalledProcessError as e:
                    st.error(f"Erreur lors de l'exécution : {e.stderr}")