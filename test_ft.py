import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("FT_CLIENT_ID")
CLIENT_SECRET = os.getenv("FT_CLIENT_SECRET")

def test_france_travail():
    print("1. Demande du token d'accès...")
    auth_url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
    
    # Utilisation des deux scopes exacts de la documentation
    auth_data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "o2dsoffre api_offresdemploiv2"
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    auth_res = requests.post(auth_url, data=auth_data, headers=headers)
    
    if auth_res.status_code != 200:
        print(f"❌ Échec de l'authentification (Code {auth_res.status_code})")
        print("Détail :", auth_res.text)
        return

    token = auth_res.json().get("access_token")
    print("✅ Authentification réussie ! Token obtenu.")

    print("\n2. Test de recherche d'offres...")
    search_url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    params = {
        "motsCles": "Développeur",
        "range": "0-4"
    }

    res = requests.get(search_url, headers=headers, params=params)

    if res.status_code in (200, 206):
        data = res.json()
        offres = data.get("resultats", [])
        print(f"✅ Recherche réussie ! {len(offres)} offres récupérées :\n")
        
        for i, offre in enumerate(offres, 1):
            titre = offre.get("intitule")
            entreprise = offre.get("entreprise", {}).get("nom", "Anonyme")
            lieu = offre.get("lieuTravail", {}).get("libelle", "Lieu non précisé")
            print(f"{i}. {titre} - {entreprise} ({lieu})")
    else:
        print(f"❌ Erreur lors de la recherche (Code {res.status_code})")
        print("Détail :", res.text)

if __name__ == "__main__":
    test_france_travail()