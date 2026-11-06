from datetime import UTC, datetime

import pytest

from ingestion.extraire import preparer

LIGNES = [{"id": 1, "ville": "Marseille", "geo": {"lat": 43.3, "lon": 5.4}}]
HEURE = datetime(2026, 11, 3, 6, 0, tzinfo=UTC)


def test_garde_les_colonnes_demandees():
    df = preparer(LIGNES, ["id", "ville"], HEURE)
    assert list(df.columns) == ["id", "ville", "extrait_le"]


def test_aplatit_les_objets_imbriques():
    df = preparer(LIGNES, ["geo_lat"], HEURE)
    assert df.loc[0, "geo_lat"] == 43.3


def test_colonne_absente_leve_une_erreur():
    with pytest.raises(ValueError):
        preparer(LIGNES, ["prix_inconnu"], HEURE)