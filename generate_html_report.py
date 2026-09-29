import sqlite3
import json
import os
import subprocess
import sys
import io

# Encodage UTF-8 sous Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_NAME = "jobs.db"
OUTPUT_HTML = "index.html"  # "index.html" est nécessaire pour GitHub Pages

def generate_html():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Sélection des offres retenues (non rejetées, triées par score IA)
    cursor.execute("""
        SELECT title, company, location, site, ai_score, ai_analysis, job_url, date_posted
        FROM jobs
        WHERE status != 'rejected' AND ai_score >= 50
        ORDER BY ai_score DESC
    """)
    jobs = cursor.fetchall()
    conn.close()

    job_cards_html = ""

    for job in jobs:
        title, company, location, site, ai_score, ai_analysis, job_url, date_posted = job
        
        competences_html = ""
        explication = ""
        points_forts_html = ""
        points_faibles_html = ""

        if ai_analysis:
            try:
                analysis = json.loads(ai_analysis)
                explication = analysis.get("explication", "")
                
                # Récupération des compétences / mots-clés
                keywords = analysis.get("competences_cles") or analysis.get("tags", [])
                for kw in keywords:
                    competences_html += f'<span class="badge">{kw}</span> '

                # Points forts
                for pf in analysis.get("points_forts", []):
                    points_forts_html += f'<li>✅ {pf}</li>'

                # Points de vigilance
                for pf in analysis.get("points_faibles", []):
                    points_faibles_html += f'<li>⚠️ {pf}</li>'

            except Exception:
                explication = str(ai_analysis)

        # Couleur du badge de score
        score_class = "score-high" if ai_score >= 70 else "score-med"

        card = f"""
        <div class="card">
            <div class="card-header">
                <div>
                    <h2 class="job-title"><a href="{job_url}" target="_blank" rel="noopener">{title}</a></h2>
                    <div class="job-meta">🏢 <strong>{company}</strong> | 📍 {location} | 🌐 {site.upper()} | 📅 {date_posted or 'Récent'}</div>
                </div>
                <div class="score-badge {score_class}">{ai_score}/100</div>
            </div>
            
            {"<div class='tags-container'>" + competences_html + "</div>" if competences_html else ""}

            {"<p class='explanation'>" + explication + "</p>" if explication else ""}

            <div class="details-grid">
                {"<div><ul class='points-list'>" + points_forts_html + "</ul></div>" if points_forts_html else ""}
                {"<div><ul class='points-list'>" + points_faibles_html + "</ul></div>" if points_faibles_html else ""}
            </div>

            <a href="{job_url}" target="_blank" rel="noopener" class="apply-btn">Consulter l'offre sur {site.capitalize()} ➔</a>
        </div>
        """
        job_cards_html += card

    html_template = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offres d'emploi sélectionnées</title>
    <style>
        :root {{
            --bg-color: #f4f6f9;
            --card-bg: #ffffff;
            --primary: #2563eb;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        header h1 {{
            margin-bottom: 5px;
            color: #0f172a;
        }}
        header p {{
            color: var(--text-muted);
            font-size: 14px;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border: 1px solid var(--border-color);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 15px;
        }}
        .job-title {{
            margin: 0 0 8px 0;
            font-size: 1.25rem;
        }}
        .job-title a {{
            color: #0f172a;
            text-decoration: none;
        }}
        .job-title a:hover {{
            color: var(--primary);
        }}
        .job-meta {{
            font-size: 0.9rem;
            color: var(--text-muted);
        }}
        .score-badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9rem;
            white-space: nowrap;
        }}
        .score-high {{ background-color: #dcfce7; color: #166534; }}
        .score-med {{ background-color: #fef9c3; color: #854d0e; }}
        
        .tags-container {{
            margin: 12px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .badge {{
            background-color: #eff6ff;
            color: #1d4ed8;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .explanation {{
            font-size: 0.95rem;
            line-height: 1.5;
            color: #334155;
            background-color: #f8fafc;
            padding: 10px 12px;
            border-radius: 6px;
            border-left: 3px solid var(--primary);
        }}
        .details-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 10px;
        }}
        @media (max-width: 600px) {{
            .details-grid {{ grid-template-columns: 1fr; }}
            .card-header {{ flex-direction: column; }}
        }}
        .points-list {{
            margin: 0;
            padding-left: 15px;
            font-size: 0.88rem;
            color: #475569;
        }}
        .apply-btn {{
            display: inline-block;
            margin-top: 15px;
            padding: 10px 16px;
            background-color: var(--primary);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            text-align: center;
        }}
        .apply-btn:hover {{
            background-color: #1d4ed8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Sélection d'Offres d'Emploi</h1>
            <p>{len(jobs)} offre(s) retenue(s) selon tes critères</p>
        </header>

        {job_cards_html if job_cards_html else "<p style='text-align:center;'>Aucune nouvelle offre ne correspond aux critères pour le moment.</p>"}
    </div>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✅ Rapport HTML généré avec succès dans `{OUTPUT_HTML}` ({len(jobs)} offres).")

if __name__ == "__main__":
    generate_html()