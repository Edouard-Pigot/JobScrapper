import sqlite3

DB_NAME = "jobs.db"

def init_db():
    """Initialise la base de données et crée la table 'jobs' si elle n'existe pas."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_url TEXT PRIMARY KEY,
        site TEXT,
        title TEXT,
        company TEXT,
        location TEXT,
        date_posted TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Champs réservés pour le filtrage par IA
        ai_score INTEGER DEFAULT NULL,
        ai_analysis TEXT DEFAULT NULL,
        status TEXT DEFAULT 'pending' -- 'pending', 'matched', 'rejected'
    )
    """)
    
    conn.commit()
    conn.close()

def insert_jobs(df):
    """Insère les nouvelles offres dans la BDD en ignorant les doublons."""
    if df.empty:
        print("Aucune offre à insérer.")
        return 0

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    inserted_count = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO jobs (job_url, site, title, company, location, date_posted, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get("job_url", "")),
                str(row.get("site", "")),
                str(row.get("title", "")),
                str(row.get("company", "")),
                str(row.get("location", "")),
                str(row.get("date_posted", "")),
                str(row.get("description", ""))
            ))
            inserted_count += 1
        except sqlite3.IntegrityError:
            # L'URL existe déjà en base, on l'ignore
            pass

    conn.commit()
    conn.close()
    print(f"📊 {inserted_count} nouvelle(s) offre(s) enregistrée(s) dans 'jobs.db'.")
    return inserted_count