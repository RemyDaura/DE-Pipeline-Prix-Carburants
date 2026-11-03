"""Charge le dernier fichier Parquet dans BigQuery (table brute partitionnée par jour)."""
import os
import sys
from pathlib import Path

from google.cloud import bigquery

PROJET = os.environ["GCP_PROJECT_ID"]
TABLE = f"{PROJET}.raw.prix_carburants"


def dernier_fichier(dossier: Path = Path("data")) -> Path:
    """Renvoie le fichier prix_AAAA-MM-JJ.parquet le plus récent."""
    fichiers = sorted(dossier.glob("prix_*.parquet"))
    if not fichiers:
        raise SystemExit("Aucun fichier dans data/ : lance d'abord ingestion.extraire.")
    return fichiers[-1]


def charger(chemin: Path) -> int:
    """Ajoute le fichier à la table brute avec un load job (autorisé dans le bac à sable)."""
    client = bigquery.Client(project=PROJET)
    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="extrait_le",
        ),
    )
    with chemin.open("rb") as fichier:
        job = client.load_table_from_file(fichier, TABLE, job_config=config)
    job.result()
    return job.output_rows


if __name__ == "__main__":
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else dernier_fichier()
    lignes = charger(chemin)
    print(f"{lignes} lignes de {chemin.name} chargées dans {TABLE}")