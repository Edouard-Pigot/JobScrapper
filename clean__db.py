import re
import sqlite3

DB_NAME = "jobs.db"

ALLOWED_LOCATIONS = [
    "Paris", "75", "Hauts-de-Seine", "92", "Île-de-France", "Ile-de-France",
    "78", "Yvelines",
    "Télétravail", "Remote"
]

def is_valid_location(location_str):
    if not location_str:
        return True
    for loc in ALLOWED_LOCATIONS:
        pattern = r'\b' + re.escape(loc) + r'\b'
        if re.search(pattern, location_str, re.IGNORECASE):
            return True
    return False

def clean_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT job_url, location, title FROM jobs")
    rows = cursor.fetchall()
    
    deleted = 0
    for job_url, location, title in rows:
        if not is_valid_location(location):
            cursor.execute("DELETE FROM jobs WHERE job_url = ?", (job_url,))
            deleted += 1
            print(f"🗑️ Supprimé : {title} ({location})")
            
    conn.commit()
    conn.close()
    print(f"\n✅ Nettoyage terminé : {deleted} offre(s) hors zone supprimée(s).")

if __name__ == "__main__":
    clean_database()