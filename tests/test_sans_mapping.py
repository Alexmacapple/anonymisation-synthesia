"""Tests du mode sans mapping — scan de toutes les valeurs string."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.moteur.pipeline import process_text
from app.moteur.substitution import TokenTable
from app.moteur.scoring import RiskScorer, Stats


def test_process_text_email_detecte():
    result = process_text("jean.dupont@example.com", detection_mode="regex")
    assert '[EMAIL_' in result['texte_pseudonymise']


def test_process_text_json_stringifie():
    """Simule un champ JSON stringifié scanné directement."""
    json_str = '{"Firstname":"Marie","Email":"marie@test.fr","Question":"Bonjour"}'
    result = process_text(json_str, detection_mode="regex")
    assert 'marie@test.fr' not in result['texte_pseudonymise']


def test_sans_mapping_dict_toutes_valeurs():
    """Vérifie que sans mapping, toutes les valeurs string sont scannées."""
    from app.moteur.pipeline import process_record
    record = {
        "id": 123,
        "champ1": "Contact jean@test.fr merci",
        "champ2": "Appelez le 06 12 34 56 78",
        "champ3": 42,  # pas string, ignoré
    }
    tokens = TokenTable()
    stats = Stats()
    scorer = RiskScorer()
    # Sans mapping = toutes les valeurs string scannées
    # On utilise process_text sur chaque valeur (comme la CLI corrigée)
    for key, val in record.items():
        if isinstance(val, str) and val.strip():
            result = process_text(val, detection_mode="regex", tokens=tokens, stats=stats, scorer=scorer)
            record[key] = result['texte_pseudonymise']

    assert 'jean@test.fr' not in record['champ1']
    assert '06 12 34 56 78' not in record['champ2']
    assert record['champ3'] == 42  # non modifié
    assert record['id'] == 123  # non modifié


def test_api_sans_mapping():
    """Route /fichier/anonymise sans mapping."""
    import json
    import tempfile
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Créer un fichier JSON simple
    data = [{"nom": "Dupont", "email": "jean@test.fr", "commentaire": "Texte normal"}]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f)
        path = f.name

    try:
        resp = client.post("/fichier/anonymise", json={
            "path": path,
            "mode": "pseudo",
            "detection_mode": "regex",
            "dry_run": True,
        })
        assert resp.status_code == 200
        result = resp.json()
        assert result['remplacements'] >= 1, "Au moins 1 remplacement attendu (email)"
    finally:
        os.unlink(path)
