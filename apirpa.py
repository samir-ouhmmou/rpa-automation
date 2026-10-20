#!/usr/bin/env python3
"""
TP 3 - Automatisation Python / API
Suivi automatique des températures d'une ville avec l'API Open-Meteo.

Usage :
    python meteo_tp3.py                # ville par défaut : Oujda
    python meteo_tp3.py "Casablanca"   # autre ville

Dépendances : pip install requests pandas
"""

import sys
from datetime import datetime

import pandas as pd
import requests

VILLE_PAR_DEFAUT = "Oujda"
FICHIER_SORTIE = "meteo_resume.csv"
TIMEOUT = 10  # secondes

URL_GEOCODAGE = "https://geocoding-api.open-meteo.com/v1/search"
URL_PREVISION = "https://api.open-meteo.com/v1/forecast"


# --------------------------------------------------------------------------
# Partie 4 : appel API sécurisé (connexion, statut HTTP, JSON)
# --------------------------------------------------------------------------
def appeler_api(url, params):
    try:
        reponse = requests.get(url, params=params, timeout=TIMEOUT)
        reponse.raise_for_status()           # erreurs HTTP 4xx / 5xx
        return reponse.json()                # JSON invalide -> ValueError
    except requests.exceptions.ConnectionError:
        sys.exit("[ERREUR] Pas de connexion Internet (ou serveur injoignable).")
    except requests.exceptions.Timeout:
        sys.exit(f"[ERREUR] Délai dépassé ({TIMEOUT}s) : l'API ne répond pas.")
    except requests.exceptions.HTTPError as e:
        sys.exit(f"[ERREUR] Réponse incorrecte de l'API : {e}")
    except ValueError:
        sys.exit("[ERREUR] La réponse de l'API n'est pas un JSON valide.")


# --------------------------------------------------------------------------
# Partie 1 : récupération des données
# --------------------------------------------------------------------------
def trouver_coordonnees(ville):
    data = appeler_api(URL_GEOCODAGE, {"name": ville, "count": 1, "language": "fr"})
    resultats = data.get("results")
    if not resultats:
        sys.exit(f"[ERREUR] Ville introuvable : {ville}")
    r = resultats[0]
    return r["latitude"], r["longitude"], r.get("name", ville), r.get("country", "")


def recuperer_meteo(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean",
        "past_days": 7,
        "forecast_days": 7,
        "timezone": "auto",
    }
    return appeler_api(URL_PREVISION, params)


def extraire_donnees(data):
    """Extrait dates et températures ; vérifie la structure de la réponse."""
    daily = data.get("daily")
    cles = ["time", "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean"]
    if not daily or any(c not in daily for c in cles):
        sys.exit("[ERREUR] Données incomplètes : champs attendus absents de la réponse.")
    longueurs = {len(daily[c]) for c in cles}
    if len(longueurs) != 1 or 0 in longueurs:
        sys.exit("[ERREUR] Données incohérentes ou vides.")

    return pd.DataFrame({
        "date": daily["time"],
        "temp_max": daily["temperature_2m_max"],
        "temp_min": daily["temperature_2m_min"],
        "temp_moy": daily["temperature_2m_mean"],
    })


# --------------------------------------------------------------------------
# Partie 2 : traitement
# --------------------------------------------------------------------------
def traiter(df):
    # Détection des valeurs manquantes
    manquantes = int(df[["temp_max", "temp_min", "temp_moy"]].isna().sum().sum())
    if manquantes:
        print(f"[ATTENTION] {manquantes} valeur(s) manquante(s) ignorée(s) dans les calculs.")
    else:
        print("[OK] Aucune valeur manquante.")

    if df["temp_moy"].dropna().empty:
        sys.exit("[ERREUR] Aucune température exploitable.")

    return {
        "Température moyenne (°C)": round(df["temp_moy"].mean(), 2),
        "Température minimale (°C)": df["temp_min"].min(),
        "Température maximale (°C)": df["temp_max"].max(),
        "Valeurs manquantes": manquantes,
    }


# --------------------------------------------------------------------------
# Partie 3 : génération du fichier CSV (données + résumé)
# --------------------------------------------------------------------------
def ecrire_fichier(df, resume, ville, pays):
    with open(FICHIER_SORTIE, "w", encoding="utf-8-sig", newline="") as f:
        f.write(f"Ville;{ville} ({pays})\n")
        f.write(f"Généré le;{datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
        df.to_csv(f, sep=";", index=False)
        f.write("\nRESUME\n")
        for k, v in resume.items():
            f.write(f"{k};{v}\n")
    print(f"[OK] Fichier généré : {FICHIER_SORTIE}")


def verifier_fichier():
    with open(FICHIER_SORTIE, encoding="utf-8-sig") as f:
        contenu = f.read()
    print("\n--- Contenu du fichier ---")
    print(contenu)


# --------------------------------------------------------------------------
def main():
    ville = sys.argv[1] if len(sys.argv) > 1 else VILLE_PAR_DEFAUT
    print(f"Exécution du {datetime.now():%Y-%m-%d %H:%M:%S} - ville : {ville}")

    lat, lon, nom, pays = trouver_coordonnees(ville)
    print(f"[OK] Coordonnées : {lat}, {lon}")

    data = recuperer_meteo(lat, lon)
    df = extraire_donnees(data)
    print(f"[OK] {len(df)} jours reçus.")
    print(df.head())

    resume = traiter(df)
    ecrire_fichier(df, resume, nom, pays)
    verifier_fichier()


if __name__ == "__main__":
    main()