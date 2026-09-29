import json
import re
import sqlite3
import sys
import ollama

DB_NAME = "jobs.db"
MODEL_NAME = "gemma4"

def load_profile():
    with open("profile.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_pending_jobs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_url, title, company, location, description 
        FROM jobs 
        WHERE status = 'pending'
    """)
    jobs = cursor.fetchall()
    conn.close()
    return jobs

def update_job_evaluation(job_url, score, analysis, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs 
        SET ai_score = ?, ai_analysis = ?, status = ?
        WHERE job_url = ?
    """, (score, json.dumps(analysis, ensure_ascii=False), status, job_url))
    conn.commit()
    conn.close()

def has_excluded_tech(title, description, excluded_techs):
    text_to_check = f"{title} {description[:1000]}"
    for tech in excluded_techs:
        pattern = r'\b' + re.escape(tech) + r'\b'
        if re.search(pattern, text_to_check, re.IGNORECASE):
            return tech
    return None

def evaluate_job(job, profile):
    job_url, title, company, location, description = job
    
    # 1. Filtre pré-IA : Technos exclues
    excluded_techs = profile.get("technologies_exclues", [])
    found_excluded = has_excluded_tech(title, description or "", excluded_techs)
    
    if found_excluded:
        print(f"   🚫 Techno exclue ({found_excluded}) ➔ Score 0.")
        return {
            "score": 0,
            "tags": [found_excluded],
            "explication": f"Offre axée sur une technologie non souhaitée ({found_excluded}).",
            "points_forts": [],
            "points_faibles": [f"Technologie exclue : {found_excluded}"]
        }

    clean_description = description[:1500] if description else "Pas de description"

    prompt = f"""
Tu es un assistant RH ultra-sélectionneur pour un développeur C++ / Web / 3D.
Évalue la correspondance entre le profil du candidat et l'offre ci-dessous et extrais les langages/technologies clés demandés.

PROFIL CANDIDAT :
- Titre : {profile['titre_recherche']}
- Compétences clés : {", ".join(profile['competences_clefs'])}
- Technologies STRICTEMENT EXCLUES : {", ".join(profile.get('technologies_exclues', []))}

OFFRE D'EMPLOI :
- Titre : {title}
- Entreprise : {company}
- Localisation : {location}
- Description :
{clean_description}

CONSIGNES STRICTES :
1. Si l'offre requiert principalement une techno exclue (Java, Spring, C#, .NET, PHP...), met le score à 0.
2. N'attribue un score > 70 que si le cœur du poste concerne le C++, le Web (React, TS...) ou la 3D/WebGL/Cartographie.
3. Extrais une liste de 3 à 6 mots-clés/tags représentant les langages, frameworks et outils principaux demandés (ex: ["C++", "WebGL", "React", "Docker"]).

Réponds EXCLUSIVEMENT sous la forme d'un objet JSON valide structuré comme suit :
{{
  "score": <nombre entre 0 et 100>,
  "tags": ["<Techno1>", "<Techno2>", "<Techno3>"],
  "explication": "<résumé synthétique en 2 phrases>",
  "points_forts": ["<point 1>", "<point 2>"],
  "points_faibles": ["<point 1>", "<point 2>"]
}}
"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            format="json",
            options={
                "temperature": 0.1,
                "repeat_penalty": 1.2
            }
        )
        return json.loads(response['message']['content'])
    except Exception as e:
        print(f"   ❌ Erreur d'évaluation : {e}")
        return None

def main():
    profile = load_profile()
    
    pending_jobs = get_pending_jobs()
    total = len(pending_jobs)
    print(f"🚀 Analyse IA locale sur {total} offre(s)...\n")

    for index, job in enumerate(pending_jobs, 1):
        job_url, title, company, location, _ = job
        print(f"[{index}/{total}] {title} - {company} ({location})")
        
        eval_result = evaluate_job(job, profile)
        
        if eval_result and "score" in eval_result:
            score = eval_result.get("score", 0)
            status = "matched" if score >= 60 else "rejected"
            update_job_evaluation(job_url, score, eval_result, status)
            print(f"   Score : {score}/100 ➔ Statut : {status}")

    print("\n✅ Réévaluation terminée !")

if __name__ == "__main__":
    main()