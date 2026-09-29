import os
import re
import requests
import pandas as pd
from dotenv import load_dotenv
from database import init_db, insert_jobs
from jobspy import scrape_jobs

load_dotenv()

SEARCH_TERMS = [
    "Développeur", 
    "Développeur Web", 
    "Développeur Jeux Vidéo", 
    "Développeur Front-End", 
    "Ingénieur Logiciel",
    "Développeur C++"
]

# Mots-clés indiquant un stage ou une alternance à exclure
EXCLUDED_KEYWORDS = [
    r"\bstage\b",
    r"\bstagiaire\b",
    r"\binternship\b",
    r"\bintern\b",
    r"\balternance\b",
    r"\balternant\b",
    r"\bapprentissage\b",
    r"\bapprenti\b",
    r"\btrainee\b",
    r"\bvie\b"
]

# Zones autorisées (Mots-clés / Départements / Villes / Télétravail)
ALLOWED_LOCATIONS = [
    "Paris", "75", "Hauts-de-Seine", "92", "Île-de-France", "Ile-de-France", "78", "Yvelines", "94", "Val-de-Marne", "Chaville", "Boulogne-Billancourt", "Neuilly-sur-Seine", "Versailles", "Saint-Cloud", "Rueil-Malmaison",
    "Issy-les-Moulineaux", "Levallois-Perret", "Suresnes", "Clamart", "Meudon", "Puteaux", "Courbevoie", "Saint-Denis", "Montreuil", "Nanterre", "Clichy", "Asnières-sur-Seine",
    "Chatillon", "Malakoff", "Vanves", "Montrouge", "Ivry-sur-Seine", "Vitry-sur-Seine", "Saint-Maur-des-Fossés", "Créteil", "Maisons-Alfort", "Alfortville", "Charenton-le-Pont", "Joinville-le-Pont",
    "Massy", "Palaiseau", "Saclay", "Vélizy-Villacoublay", "Sceaux", "Châtenay-Malabry", "Bagneux", "Fontenay-aux-Roses", "Clamart", "Le Plessis-Robinson", "Chaville", "Ville-d'Avray", "Sèvres", "Meudon-la-Forêt"
    "Télétravail", "Remote"
]

def is_valid_location(location_str):
    """Vérifie si la localisation de l'offre contient au moins une zone autorisée."""
    if not location_str or pd.isna(location_str):
        return True  # En cas d'absence d'info de lieu, on conserve par précaution

    location_str = str(location_str)
    for loc in ALLOWED_LOCATIONS:
        # Recherche par mot ou code départemental
        pattern = r'\b' + re.escape(loc) + r'\b'
        if re.search(pattern, location_str, re.IGNORECASE):
            return True
    return False

def is_unwanted_contract(title, description=""):
    """Vérifie si le titre ou le début de la description contient un mot-clé de stage/alternance."""
    text_to_check = f"{title} {description[:300]}"
    for pattern in EXCLUDED_KEYWORDS:
        if re.search(pattern, text_to_check, re.IGNORECASE):
            return True
    return False

# 1. JOBSPY (LinkedIn, Indeed, Google)
def fetch_jobspy_jobs(search_terms, locations=["Paris, France"], results_wanted=30):
    all_jobs = []
    print("--- Scraping JobSpy (LinkedIn, Indeed, Google) ---")
    
    for loc in locations:
        for term in search_terms:
            print(f"Recherche JobSpy : '{term}' à {loc}")
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "indeed", "google"],
                    search_term=term,
                    location=loc,
                    results_wanted=results_wanted,
                    hours_old=72,
                    country_indeed='France',
                    linkedin_fetch_description=True
                )
                if not jobs.empty:
                    all_jobs.append(jobs)
            except Exception as e:
                print(f"Erreur JobSpy pour {term} ({loc}): {e}")
            
    return pd.concat(all_jobs, ignore_index=True) if all_jobs else pd.DataFrame()

# 2. APEC
def fetch_apec_jobs(search_terms, departements=["75", "92"], results_wanted=20):
    print("--- Récupération offres APEC ---")
    url = "https://www.apec.fr/cms/webservices/rechercheOffre"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }
    apec_jobs = []
    
    for term in search_terms:
        payload = {
            "motsCles": term,
            "lieux": departements,
            "page": 0,
            "nombrePostes": results_wanted,
            "sorts": [{"type": "SCORE", "direction": "DESC"}]
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                for offer in response.json().get("resultats", []):
                    apec_jobs.append({
                        "site": "apec",
                        "title": offer.get("intitule"),
                        "company": offer.get("nomEntreprise"),
                        "location": offer.get("lieuTexte"),
                        "date_posted": offer.get("datePublication"),
                        "job_url": f"https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/{offer.get('id')}",
                        "description": offer.get("texteOffre", "")
                    })
        except Exception as e:
            print(f"Erreur APEC pour {term}: {e}")

    return pd.DataFrame(apec_jobs) if apec_jobs else pd.DataFrame()

# 3. FRANCE TRAVAIL
def fetch_france_travail_jobs(search_terms, departements=["75", "92"], results_wanted=20):
    client_id = os.getenv("FT_CLIENT_ID")
    client_secret = os.getenv("FT_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("⚠️ Identifiants France Travail non trouvés dans .env")
        return pd.DataFrame()

    print("--- Récupération offres France Travail ---")
    auth_url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
    
    auth_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "o2dsoffre api_offresdemploiv2"
    }
    headers_auth = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        auth_res = requests.post(auth_url, data=auth_data, headers=headers_auth)
        if auth_res.status_code != 200:
            print(f"Erreur authentification FT ({auth_res.status_code}): {auth_res.text}")
            return pd.DataFrame()
        token = auth_res.json().get("access_token")
    except Exception as e:
        print(f"Erreur connexion France Travail: {e}")
        return pd.DataFrame()

    headers_api = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    search_url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    ft_jobs = []

    for dep in departements:
        for term in search_terms:
            params = {
                "motsCles": term,
                "departement": dep,
                "range": f"0-{results_wanted}"
            }
            try:
                res = requests.get(search_url, headers=headers_api, params=params)
                if res.status_code in (200, 206):
                    for offer in res.json().get("resultats", []):
                        ft_jobs.append({
                            "site": "france_travail",
                            "title": offer.get("intitule"),
                            "company": offer.get("entreprise", {}).get("nom", "Anonyme"),
                            "location": offer.get("lieuTravail", {}).get("libelle"),
                            "date_posted": offer.get("dateCreation"),
                            "job_url": offer.get("origineOffre", {}).get("urlOrigine", f"https://candidat.francetravail.fr/offres/recherche/detail/{offer.get('id')}"),
                            "description": offer.get("description", "")
                        })
            except Exception as e:
                print(f"Erreur France Travail pour {term} ({dep}): {e}")

    return pd.DataFrame(ft_jobs) if ft_jobs else pd.DataFrame()

# EXÉCUTION DU SCRAPER
if __name__ == "__main__":
    init_db()
    
    df_jobspy = fetch_jobspy_jobs(SEARCH_TERMS)
    df_apec = fetch_apec_jobs(SEARCH_TERMS)
    df_ft = fetch_france_travail_jobs(SEARCH_TERMS)
    
    all_results = pd.concat([df_jobspy, df_apec, df_ft], ignore_index=True)
    
    if not all_results.empty:
        initial_count = len(all_results)
        
        # 1. Filtre géographique
        all_results = all_results[all_results["location"].apply(is_valid_location)]
        
        # 2. Exclusions des stages et alternances
        all_results = all_results[~all_results.apply(
            lambda row: is_unwanted_contract(row["title"], row.get("description", "")), axis=1
        )]
        
        filtered_count = len(all_results)
        print(f"🎯 Filtrage (Lieu & Contrat) : {filtered_count}/{initial_count} offres conservées.")
        
        all_results = all_results.drop_duplicates(subset=["job_url"])
        insert_jobs(all_results)
    else:
        print("Aucune offre récupérée.")