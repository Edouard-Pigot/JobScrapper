import subprocess
import os

def deploy():
    print("1. Génération du rapport HTML...")
    subprocess.run(["python", "generate_html_report.py"], check=True)

    print("2. Publication sur GitHub...")
    try:
        subprocess.run(["git", "add", "index.html"], check=True)
        subprocess.run(["git", "commit", "-m", "Mise à jour automatique des offres"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("\n🚀 Rapport publié sur GitHub Pages avec succès !")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Note lors du déploiement Git : {e}")

if __name__ == "__main__":
    deploy()