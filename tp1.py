import time
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------ CONFIG ----
FICHIER_EXCEL = "contacts_test_marocains.xlsx"
FORMULAIRE = Path("formulaire.html").resolve().as_uri()
GMAIL_USER = "ouhmmousamir@gmail.com"          # 
GMAIL_APP_PASSWORD = ""     # le mot de passe je lai supprime
ENVOYER_EMAILS = True                          # False = tester seulement le formulair


# ---------- etape 2 : lecture Excel ----------
df = pd.read_excel(FICHIER_EXCEL)
print(df.head(5))
print(f"\n{len(df)} lignes chargées.\n")


# ---------- etape 4 : envoi d'email ----------
def envoyer_email(destinataire, nom, message):
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = destinataire
    msg["Subject"] = f"Bonjour {nom}, nous avons bien reçu votre message"

    corps = (
        f"Bonjour {nom},\n\n"
        f"Merci pour votre message :\n\"{message}\"\n\n"
        f"Nous reviendrons vers vous très prochainement.\n\n"
        f"Cordialement,\nL'équipe"
    )
    msg.attach(MIMEText(corps, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
        serveur.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        serveur.send_message(msg)


# ---------- etape 3 : remplir le formulaire avec Selenium ----------
driver = webdriver.Chrome()      # Selenium 4 télécharge le driver automatiquement
driver.maximize_window()
driver.get(FORMULAIRE)
attente = WebDriverWait(driver, 10)

envoyes, erreurs = 0, []

# ---------- etape 5 : exécution et validation ----------
for i, ligne in df.iterrows():
    nom, email, message = str(ligne["Nom"]), str(ligne["Email"]), str(ligne["Message"])
    print(f"[{i + 1}/{len(df)}] {nom} - {email}")

    # Remplir le formulaire
    attente.until(EC.element_to_be_clickable((By.ID, "nom"))).send_keys(nom)
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "message").send_keys(message)
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    time.sleep(1)   # petit délai entre chaque ligne

    # Envoyer l'email personnalisé
    if ENVOYER_EMAILS:
        try:
            envoyer_email(email, nom, message)
            envoyes += 1
        except Exception as e:
            erreurs.append((email, str(e)))
            print(f"   ! Erreur email : {e}")

# Validation : on compte les lignes enregistrées par la page
saisies = len(driver.find_elements(By.CSS_SELECTOR, "#log li"))
print(f"\nLignes Excel : {len(df)} | Lignes saisies dans le formulaire : {saisies}")
print("Validation formulaire :", "OK" if saisies == len(df) else "ERREUR")
print(f"Emails envoyés : {envoyes} | Erreurs : {len(erreurs)}")
for adresse, err in erreurs:
    print(" -", adresse, ":", err)

time.sleep(3)
driver.quit()