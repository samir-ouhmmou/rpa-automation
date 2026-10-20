import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# ==========================================
# TP4 : Web Scraping et ETL avec Books to Scrape
# ==========================================

URL = "https://books.toscrape.com/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}


# ==========================================
# PARTIE 1 : EXTRACTION
# ==========================================

def extraire_produits(url):
    produits = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select("article.product_pod")

        for article in articles:
            titre_element = article.select_one("h3 a")
            prix_element = article.select_one("p.price_color")
            note_element = article.select_one("p.star-rating")
            disponibilite_element = article.select_one(
                "p.instock.availability"
            )

            # L'attribut 'title' contient le nom complet sans troncature
            titre = (
                titre_element.get("title") or titre_element.get_text(strip=True)
                if titre_element else None
            )

            prix_texte = (
                prix_element.get_text(strip=True)
                if prix_element else None
            )

            # La note est exprimée sous forme de classe CSS (ex: ['star-rating', 'Three'])
            classes_note = note_element.get("class", []) if note_element else []
            note_texte = classes_note[1] if len(classes_note) > 1 else None

            disponibilite = (
                disponibilite_element.get_text(strip=True)
                if disponibilite_element else "Non précisée"
            )

            produits.append({
                "titre": titre,
                "prix": prix_texte,
                "disponibilite": disponibilite,
                "note": note_texte
            })

        return produits

    except requests.RequestException as erreur:
        print("Erreur lors de la connexion au site web :", erreur)
        return []


# ==========================================
# PARTIE 2 : NETTOYAGE ET TRANSFORMATION
# ==========================================

def nettoyer_donnees(produits):
    df = pd.DataFrame(
        produits,
        columns=["titre", "prix", "disponibilite", "note"]
    )

    nombre_initial = len(df)

    # Supprimer les doublons
    df = df.drop_duplicates()

    # Supprimer les lignes sans titre ou prix
    df = df.dropna(subset=["titre", "prix"])

    # Nettoyer et convertir les prix en nombres
    def convertir_prix(valeur):
        if pd.isna(valeur):
            return None

        valeur = str(valeur).replace(",", "")
        correspondance = re.search(r"\d+(?:\.\d+)?", valeur)

        return float(correspondance.group()) if correspondance else None

    df["prix"] = df["prix"].apply(convertir_prix)

    # Nettoyer les notes (ex: "Three" -> 3.0 ou "4.5 out of 5" -> 4.5)
    mapping_notes = {
        "One": 1.0,
        "Two": 2.0,
        "Three": 3.0,
        "Four": 4.0,
        "Five": 5.0
    }

    def convertir_note(valeur):
        if pd.isna(valeur):
            return None

        valeur_str = str(valeur).strip()
        if valeur_str in mapping_notes:
            return mapping_notes[valeur_str]

        correspondance = re.search(r"\d+(?:\.\d+)?", valeur_str)
        return float(correspondance.group()) if correspondance else None

    df["note"] = df["note"].apply(convertir_note)

    # Supprimer les prix non convertibles
    df = df.dropna(subset=["prix"])

    # Organiser les colonnes
    df = df[
        ["titre", "prix", "disponibilite", "note"]
    ].reset_index(drop=True)

    print("Produits extraits :", nombre_initial)
    print("Produits conservés après nettoyage :", len(df))

    return df


# ==========================================
# PARTIE 3 : EXPORTATION
# ==========================================

def exporter_donnees(df):
    df.to_csv("produits_site.csv", index=False, encoding="utf-8-sig")
    df.to_excel("produits_site.xlsx", index=False, engine="openpyxl")

    # Vérification des deux fichiers
    csv_df = pd.read_csv("produits_site.csv")
    excel_df = pd.read_excel("produits_site.xlsx")

    print("Fichier CSV créé : produits_site.csv")
    print("Fichier Excel créé : produits_site.xlsx")

    print(
        "Les deux fichiers contiennent les mêmes données :",
        csv_df.equals(excel_df)
    )



def main():
    print("Début du processus ETL du site web...")

    produits = extraire_produits(URL)

    if not produits:
        print(
            "Aucun produit extrait. Le site web peut avoir bloqué la requête "
            "ou modifié la structure de sa page."
        )
        return

    df = nettoyer_donnees(produits)

    if df.empty:
        print("Aucune donnée valide à exporter.")
        return

    exporter_donnees(df)

    print("\nAperçu des produits :")
    print(df.head(10).to_string(index=False))

    print("\nProcessus ETL terminé.")


if __name__ == "__main__":
    main()

    main()