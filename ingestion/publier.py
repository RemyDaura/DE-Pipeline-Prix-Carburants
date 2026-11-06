"""Prépare le relevé du jour (site/releve.json), lu par le portfolio.

Lancé juste après `dbt build` : lit les marts dans BigQuery et le résultat des tests
dbt (dbt/target/run_results.json), vérifie le contrat de données, puis écrit le
fichier publié sur GitHub Pages. Si le contrat n'est pas respecté, rien n'est écrit
et le pipeline s'arrête : le site continue d'afficher le dernier relevé valide.
"""
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from google.cloud import bigquery

# Ordre d'affichage sur le site -> nom du carburant dans les marts
CARBURANTS = {
    "gazole": "Gazole",
    "sp98": "SP98",
    "sp95": "SP95",
    "e10": "E10",
    "gplc": "GPLc",
    "e85": "E85",
}

# Mêmes bornes que le test dbt assert_prix_dans_bornes
PRIX_MIN = 0.30
PRIX_MAX = 4.00

# Dataset des marts : "analytics" en CI (profil ci/profiles.yml), "dbt_dev" pour tester en local
DATASET = os.environ.get("DATASET_MARTS", "analytics")

RUN_RESULTS = Path("dbt/target/run_results.json")
SORTIE = Path("site/releve.json")

# Moyennes exactes du dernier jour : somme des prix / nombre de stations,
# pour la France entière et pour les Bouches-du-Rhône (13)
REQUETE_PRIX = """
with dernier_jour as (
    select max(jour) as jour
    from `{projet}.{dataset}.mart_prix_jour_departement`
)

select
    m.jour,
    m.carburant,
    round(sum(m.somme_prix) / sum(m.nb_stations), 4) as france,
    round(
        sum(if(m.code_departement = '13', m.somme_prix, 0))
        / nullif(sum(if(m.code_departement = '13', m.nb_stations, 0)), 0),
        4
    ) as bouches_du_rhone
from `{projet}.{dataset}.mart_prix_jour_departement` as m
inner join dernier_jour as d on m.jour = d.jour
group by m.jour, m.carburant
"""

# Stations présentes dans les relevés chargés ce jour-là
REQUETE_STATIONS = """
select count(distinct id) as nb_stations
from `{projet}.raw.prix_carburants`
where date(extrait_le, 'Europe/Paris') = @jour
"""


def compter_tests(run_results: dict) -> dict:
    """Compte les tests d'un `dbt build` : total, échecs et avertissements."""
    commande = run_results.get("args", {}).get("which")
    if commande != "build":
        raise ValueError(f"run_results.json vient de « dbt {commande} », pas de « dbt build »")
    statuts = [r["status"] for r in run_results["results"] if r["unique_id"].startswith("test.")]
    if not statuts:
        raise ValueError("aucun test dans run_results.json")
    return {
        "total": len(statuts),
        "echecs": sum(statut in ("fail", "error") for statut in statuts),
        "avertissements": statuts.count("warn"),
    }


def construire_releve(
    lignes: list[dict],
    nb_stations: int,
    tests: dict,
    genere_le: str,
    run_url: str | None = None,
) -> dict:
    """Assemble le relevé à partir des lignes du mart (une par carburant)."""
    jours = {str(ligne["jour"]) for ligne in lignes}
    if len(jours) != 1:
        raise ValueError(f"le mart doit porter sur un seul jour, trouvé : {sorted(jours)}")

    par_libelle = {ligne["carburant"]: ligne for ligne in lignes}
    carburants = []
    for code, libelle in CARBURANTS.items():
        ligne = par_libelle.get(libelle)
        if ligne is None:
            raise ValueError(f"carburant absent du mart : {libelle}")
        carburants.append(
            {
                "code": code,
                "france": ligne["france"],
                "bouches_du_rhone": ligne["bouches_du_rhone"],
            }
        )

    releve = {
        "version": 1,
        "source": "pipeline",
        "jour": jours.pop(),
        "genere_le": genere_le,
        "nb_stations": nb_stations,
        "tests": tests,
        "carburants": carburants,
    }
    if run_url:
        releve["run_url"] = run_url
    return releve


def verifier_releve(releve: dict) -> list[str]:
    """Contrat de données, identique à celui du site : renvoie les problèmes trouvés."""
    problemes = []
    if releve.get("version") != 1:
        problemes.append("version inattendue")
    if not isinstance(releve.get("nb_stations"), int) or releve["nb_stations"] <= 0:
        problemes.append("nb_stations absent ou nul")
    tests = releve.get("tests", {})
    if any(not isinstance(tests.get(cle), int) for cle in ("total", "echecs", "avertissements")):
        problemes.append("bloc tests incomplet")
    elif tests["echecs"] > 0:
        problemes.append(f"{tests['echecs']} test(s) en échec")
    for carburant in releve.get("carburants", []):
        for cle in ("france", "bouches_du_rhone"):
            prix = carburant.get(cle)
            if not isinstance(prix, (int, float)) or not PRIX_MIN <= prix <= PRIX_MAX:
                problemes.append(f"{carburant.get('code')}.{cle} hors bornes : {prix}")
    return problemes


def url_du_run() -> str | None:
    """Lien vers le run GitHub Actions en cours (absent en local)."""
    serveur = os.environ.get("GITHUB_SERVER_URL")
    depot = os.environ.get("GITHUB_REPOSITORY")
    run = os.environ.get("GITHUB_RUN_ID")
    return f"{serveur}/{depot}/actions/runs/{run}" if serveur and depot and run else None


def main() -> None:
    projet = os.environ["GCP_PROJECT_ID"]
    tests = compter_tests(json.loads(RUN_RESULTS.read_text(encoding="utf-8")))

    client = bigquery.Client(project=projet)
    resultat = client.query(REQUETE_PRIX.format(projet=projet, dataset=DATASET)).result()
    lignes = [
        {
            "jour": row["jour"],
            "carburant": row["carburant"],
            "france": _flottant(row["france"]),
            "bouches_du_rhone": _flottant(row["bouches_du_rhone"]),
        }
        for row in resultat
    ]
    if not lignes:
        raise SystemExit("Le mart mart_prix_jour_departement est vide : rien à publier.")

    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("jour", "DATE", lignes[0]["jour"])]
    )
    stations = client.query(REQUETE_STATIONS.format(projet=projet), job_config=config).result()
    nb_stations = next(iter(stations))["nb_stations"]

    releve = construire_releve(
        lignes,
        nb_stations,
        tests,
        genere_le=datetime.now(UTC).isoformat(timespec="seconds"),
        run_url=url_du_run(),
    )
    problemes = verifier_releve(releve)
    if problemes:
        raise SystemExit("Relevé non conforme, rien n'est publié :\n- " + "\n- ".join(problemes))

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(releve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Relevé du {releve['jour']} écrit dans {SORTIE} : {nb_stations} stations, "
        f"{tests['total']} tests ({tests['avertissements']} avertissement(s))"
    )


def _flottant(valeur) -> float | None:
    """BigQuery peut renvoyer des Decimal : le JSON attend des nombres simples."""
    return None if valeur is None else float(valeur)


if __name__ == "__main__":
    main()
