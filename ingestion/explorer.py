"""Affiche les champs d'une station pour choisir les colonnes à garder."""
import requests

URL = (
    "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "prix-des-carburants-en-france-flux-instantane-v2/records"
)

reponse = requests.get(URL, params={"limit": 5}, timeout=60)
reponse.raise_for_status()
donnees = reponse.json()

print("Nombre total de stations :", donnees["total_count"])
for cle, valeur in donnees["results"][0].items():
    print(f"{cle} : {valeur!r}")