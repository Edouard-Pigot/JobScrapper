import json
import re
import sqlite3
import sys
import io

# Gestion de l'encodage UTF-8 sous Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def load_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_valid_location(location_str, allowed_locations):
    if not location_str:
        return True
    location_str = str(location_str)
    for loc in allowed_locations:
        pattern = r'\b' + re.escape(loc) + r'\b'
        if re.search(pattern, location_str, re.IGNORECASE):
            return True
    return False

def has_excluded_term(title, description, excluded_terms):
    text_to_check = f"{title} {description[:1200]}"
    for term in excluded_terms:
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, text_to_check, re.IGNORECASE):
            return term
    return None

def main():
    try:
        config = load_json_file("config_params.json")
        messages = load_json_file("messages.json")
    except Exception as e:
        print(f"❌ Erreur de chargement des configurations : {e}")
        return

    db_name = config["database"]["db_name"]
    allowed_locations = config["filtering"]["allowed_locations"]
    excluded_terms = config["filtering"]["excluded_terms"]

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Sélection des offres non encore rejetées
    cursor.execute("""
        SELECT job_url, title, location, description 
        FROM jobs 
        WHERE status != 'rejected' AND (ai_score > 0 OR ai_score IS NULL)
    """)
    jobs = cursor.fetchall()

    print(messages["logs"]["processing_count"].format(count=len(jobs)))

    rejected_loc = 0
    rejected_terms = 0

    for job in jobs:
        job_url, title, location, description = job
        description = description or ""
        
        rejection_reason = None
        
        # 1. Filtrage Lieu
        if not is_valid_location(location, allowed_locations):
            rejection_reason = messages["rejection_reasons"]["location"].format(location=location)
            rejected_loc += 1
        
        # 2. Filtrage Mot-clé exclu
        if not rejection_reason:
            found_term = has_excluded_term(title, description, excluded_terms)
            if found_term:
                rejection_reason = messages["rejection_reasons"]["term"].format(term=found_term)
                rejected_terms += 1

        # Application du rejet en BDD
        if rejection_reason:
            explanation = messages["rejection_reasons"]["explanation"].format(reason=rejection_reason)
            analysis = {
                "score": 0,
                "competences_cles": [],
                "explication": explanation,
                "points_forts": [],
                "points_faibles": [rejection_reason]
            }

            cursor.execute("""
                UPDATE jobs 
                SET ai_score = 0, status = 'rejected', ai_analysis = ?
                WHERE job_url = ?
            """, (json.dumps(analysis, ensure_ascii=False), job_url))

    conn.commit()
    conn.close()

    logs_msg = messages["logs"]
    print(logs_msg["summary_title"])
    print(logs_msg["summary_location"].format(rejected_loc=rejected_loc))
    print(logs_msg["summary_terms"].format(rejected_terms=rejected_terms))
    print(logs_msg["summary_total"].format(total=rejected_loc + rejected_terms))

if __name__ == "__main__":
    main()