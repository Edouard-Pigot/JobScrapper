@echo off
chcp 65001 > nul
title Job Scrapper & AI Matcher Pipeline

echo ===================================================
echo 1/3 - Scraping des nouvelles offres...
echo ===================================================
python .\scraper.py

echo.
echo ===================================================
echo 2/3 - Analyse et scoring par l'IA locale...
echo ===================================================
python .\ai_matcher.py

echo.
echo ===================================================
echo 3/3 - Lancement du Dashboard Web Streamlit...
echo ===================================================
python -m streamlit run app.py

pause