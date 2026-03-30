"""Tests du pipeline complet — process_text et process_record."""

import copy
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.moteur.pipeline import process_text, process_record
from app.moteur.substitution import TokenTable
from app.moteur.scoring import RiskScorer, Stats


# =============================================================
#  PROCESS_TEXT (scénario A — texte brut)
# =============================================================

def test_process_text_basique():
    result = process_text("Jean Dupont, email jean@test.fr", mode="pseudo", detection_mode="regex")
    assert '[EMAIL_' in result['texte_pseudonymise']
    assert 'jean@test.fr' not in result['texte_pseudonymise']
    assert len(result['correspondances']) >= 1

def test_process_text_mode_anon():
    result = process_text("Jean Dupont, email jean@test.fr", mode="anon", detection_mode="regex")
    assert '***' in result['texte_pseudonymise']
    assert 'jean@test.fr' not in result['texte_pseudonymise']

def test_process_text_score():
    result = process_text("jean@test.fr et 06 12 34 56 78", detection_mode="regex")
    assert result['score']['total'] > 0
    assert result['score']['niveau'] in ('NUL', 'FAIBLE', 'MODÉRÉ', 'ÉLEVÉ', 'CRITIQUE')

def test_process_text_whitelist():
    result = process_text("Contact Orange au 06 12 34 56 78", detection_mode="regex", whitelist={"Orange"})
    # Orange ne doit pas être pseudonymisé
    assert 'Orange' in result['texte_pseudonymise'] or 'orange' in result['texte_pseudonymise'].lower()

def test_process_text_vide():
    result = process_text("Bonjour, comment allez-vous ?", detection_mode="regex")
    assert result['texte_pseudonymise'] == "Bonjour, comment allez-vous ?"
    assert result['stats']['total'] == 0

def test_process_text_correspondances_format():
    result = process_text("jean@test.fr", detection_mode="regex")
    for c in result['correspondances']:
        assert 'type' in c
        assert 'jeton' in c
        assert 'valeur' in c


# =============================================================
#  PROCESS_RECORD (scénario B — fichier structuré)
# =============================================================

def test_process_record_champs_sensibles():
    record = {"nom": "Dupont", "prenom": "Marie", "commentaire": "Texte normal"}
    mapping = {
        "champs_sensibles": {
            "nom": {"type": "nom", "jeton": "NOM"},
            "prenom": {"type": "prenom", "jeton": "PRENOM"},
        },
        "texte_libre": [],
    }
    tokens = TokenTable()
    result = process_record(record, mode="pseudo", detection_mode="regex", tokens=tokens, mapping=mapping)
    assert result['nom'].startswith('[NOM_')
    assert result['prenom'].startswith('[PRENOM_')
    assert result['commentaire'] == "Texte normal"

def test_process_record_texte_libre():
    record = {"commentaire": "Appelez jean@test.fr merci"}
    mapping = {
        "champs_sensibles": {},
        "texte_libre": ["commentaire"],
    }
    tokens = TokenTable()
    result = process_record(record, mode="pseudo", detection_mode="regex", tokens=tokens, mapping=mapping)
    assert 'jean@test.fr' not in result['commentaire']
    assert '[EMAIL_' in result['commentaire']

def test_process_record_sans_mapping():
    record = {"texte": "Bonjour le monde"}
    result = process_record(record, mode="pseudo", detection_mode="regex")
    assert result['texte'] == "Bonjour le monde"


# =============================================================
#  UNWRAP JSON STRINGIFIÉ
# =============================================================

def test_process_record_unwrap():
    inner = json.dumps({
        "Report": {
            "Firstname": "Marie",
            "Email": "marie@test.fr",
            "Question": "Bonjour, je vous contacte pour un problème",
        }
    })
    record = {"DOAR_IDENT": 123, "RCLMFicheReportJsonSC": inner}
    mapping = {
        "structure": {"unwrap": {"field": "RCLMFicheReportJsonSC"}},
        "champs_sensibles": {
            "Report.Firstname": {"type": "prenom", "jeton": "PRENOM"},
            "Report.Email": {"type": "email", "jeton": "EMAIL"},
        },
        "texte_libre": ["Report.Question"],
    }
    tokens = TokenTable()
    result = process_record(copy.deepcopy(record), mode="pseudo", detection_mode="regex", tokens=tokens, mapping=mapping)

    # Vérifier que le champ est re-sérialisé
    report = json.loads(result['RCLMFicheReportJsonSC'])['Report']
    assert report['Firstname'].startswith('[PRENOM_')
    assert report['Email'].startswith('[EMAIL_')


# =============================================================
#  DEDUPLICATION JETONS
# =============================================================

def test_meme_email_meme_jeton():
    tokens = TokenTable()
    result1 = process_text("contact jean@test.fr", detection_mode="regex", tokens=tokens)
    result2 = process_text("email jean@test.fr", detection_mode="regex", tokens=tokens)
    # Le même email doit produire le même jeton
    assert result1['texte_pseudonymise'].count('[EMAIL_1]') == 1
    assert result2['texte_pseudonymise'].count('[EMAIL_1]') == 1


# =============================================================
#  RESTAURATION
# =============================================================

def test_restauration():
    from app.moteur.depseudonymise import depseudonymiser_texte
    texte_anon = "[PERSONNE_1], email [EMAIL_1]"
    mapping = {"[PERSONNE_1]": "Jean Dupont", "[EMAIL_1]": "jean@test.fr"}
    texte_restaure, count = depseudonymiser_texte(texte_anon, mapping)
    assert texte_restaure == "Jean Dupont, email jean@test.fr"
    assert count == 2

def test_restauration_ordre_jetons():
    from app.moteur.depseudonymise import depseudonymiser_texte
    texte = "[PERSONNE_1] et [PERSONNE_10]"
    mapping = {"[PERSONNE_1]": "A", "[PERSONNE_10]": "B"}
    result, _ = depseudonymiser_texte(texte, mapping)
    # PERSONNE_10 doit être remplacé avant PERSONNE_1 (tri par longueur)
    assert result == "A et B"
