"""Télécharge les prix des carburants et les enregistre en Parquet."""
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL_EXPORT = (
    "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "prix-des-carburants-en-france-flux-instantane-v2/exports/json"
)

# Colonnes gardées (choisies à l'étape 1.1)
COLONNES: list[str] = [
    # Station
    "id",
    "adresse",
    "cp",
    "ville",
    "code_departement",
    "departement",
    "code_region",
    "region",
    "pop",
    "geom_lat",
    "geom_lon",
    "horaires_automate_24_24",
    # Prix et date de mise à jour par carburant
    "gazole_prix",
    "gazole_maj",
    "sp95_prix",
    "sp95_maj",
    "sp98_prix",
    "sp98_maj",
    "e10_prix",
    "e10_maj",
    "e85_prix",
    "e85_maj",
    "gplc_prix",
    "gplc_maj",
]


def telecharger(url: str = URL_EXPORT) -> list[dict]:
    """Récupère toutes les stations en une seule requête."""
    reponse = requests.get(url, timeout=300)
    reponse.raise_for_status()
    return reponse.json()


def preparer(lignes: list[dict], colonnes: list[str], horodatage: datetime) -> pd.DataFrame:
    """Aplatit le JSON, garde les colonnes voulues et ajoute l'heure d'extraction."""
    df = pd.json_normalize(lignes, sep="_")
    manquantes = [c for c in colonnes if c not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes absentes de la source : {manquantes}")
    df = df[colonnes].copy()
    df["extrait_le"] = horodatage
    return df


def sauvegarder(df: pd.DataFrame, dossier: Path, jour: date) -> Path:
    """Écrit le fichier Parquet du jour dans le dossier data/."""
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"prix_{jour.isoformat()}.parquet"
    df.to_parquet(chemin, index=False)
    return chemin


def main() -> None:
    if not COLONNES:
        raise SystemExit("Remplis d'abord la liste COLONNES (étape 1.1).")
    maintenant = datetime.now(timezone.utc)
    lignes = telecharger()
    df = preparer(lignes, COLONNES, maintenant)
    chemin = sauvegarder(df, Path("data"), maintenant.date())
    taille_mo = chemin.stat().st_size / 1_000_000
    print(f"{len(df)} lignes écrites dans {chemin} ({taille_mo:.1f} Mo)")


if __name__ == "__main__":
    main()