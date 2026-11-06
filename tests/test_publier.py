from datetime import date

import pytest

from ingestion.publier import (
    CARBURANTS,
    compter_tests,
    construire_releve,
    verifier_releve,
)

TESTS_OK = {"total": 15, "echecs": 0, "avertissements": 1}


def lignes_du_mart(jour=date(2026, 11, 6)):
    """Une ligne par carburant, comme la requête sur mart_prix_jour_departement."""
    return [
        {"jour": jour, "carburant": libelle, "france": 1.9, "bouches_du_rhone": 1.95}
        for libelle in CARBURANTS.values()
    ]


def run_results(statuts, commande="build"):
    resultats = [{"unique_id": "model.carburants.stg_prix_carburants", "status": "success"}]
    resultats += [{"unique_id": f"test.carburants.t{i}", "status": s} for i, s in enumerate(statuts)]
    return {"args": {"which": commande}, "results": resultats}


def test_compte_les_tests_par_statut():
    resultats = run_results(["pass"] * 13 + ["warn", "pass"])
    assert compter_tests(resultats) == {"total": 15, "echecs": 0, "avertissements": 1}


def test_refuse_un_fichier_qui_ne_vient_pas_de_dbt_build():
    with pytest.raises(ValueError):
        compter_tests(run_results(["success"], commande="generate"))


def test_carburants_dans_l_ordre_du_site():
    releve = construire_releve(lignes_du_mart(), 9800, TESTS_OK, "2026-11-06T05:20:00+00:00")
    assert [c["code"] for c in releve["carburants"]] == ["gazole", "sp98", "sp95", "e10", "gplc", "e85"]
    assert releve["jour"] == "2026-11-06"


def test_carburant_manquant_leve_une_erreur():
    lignes = [ligne for ligne in lignes_du_mart() if ligne["carburant"] != "E85"]
    with pytest.raises(ValueError):
        construire_releve(lignes, 9800, TESTS_OK, "2026-11-06T05:20:00+00:00")


def test_releve_conforme_sans_probleme():
    releve = construire_releve(lignes_du_mart(), 9800, TESTS_OK, "2026-11-06T05:20:00+00:00")
    assert verifier_releve(releve) == []


def test_prix_hors_bornes_ou_absent_detecte():
    lignes = lignes_du_mart()
    lignes[0]["france"] = 19.9  # prix saisi en centimes
    lignes[1]["bouches_du_rhone"] = None  # aucune station dans le 13
    releve = construire_releve(lignes, 9800, TESTS_OK, "2026-11-06T05:20:00+00:00")
    assert len(verifier_releve(releve)) == 2
