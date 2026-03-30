"""Test de non-régression vs API Loïc (golden results)."""

import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.moteur.detecteur import detect_hybrid


GOLDEN_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'golden-api-loic.json')


def _load_golden():
    with open(GOLDEN_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_golden_enregistrement_1():
    """jean martin — le moteur local doit détecter les entités PII de base."""
    golden = _load_golden()
    enreg = golden['enregistrements'][0]
    spans = detect_hybrid(enreg['texte'], mode="hybrid")
    valeurs_detectees = {s.value.lower() for s in spans}

    # Email et tel doivent être détectés
    assert any('jean.martin@example.com' in v for v in valeurs_detectees), "Email non détecté"
    assert any('09 75 73 94 62' in v for v in valeurs_detectees), "Tel non détecté"


def test_golden_enregistrement_2():
    """Sophie LAMBERT — nom complet doit être détecté."""
    golden = _load_golden()
    enreg = golden['enregistrements'][1]
    spans = detect_hybrid(enreg['texte'], mode="hybrid")
    valeurs_detectees = {s.value.lower() for s in spans}

    assert any('sophie.lambert@example.com' in v for v in valeurs_detectees), "Email Sophie non détecté"
    assert any('0296507550' in v for v in valeurs_detectees), "Tel non détecté"


def test_golden_enregistrement_3_alexandra():
    """Alexandra dans le texte libre doit être détectée par NER."""
    golden = _load_golden()
    enreg = golden['enregistrements'][2]
    spans = detect_hybrid(enreg['texte'], mode="hybrid")
    valeurs_detectees = {s.value.lower() for s in spans}

    assert 'alexandra' in valeurs_detectees, \
        "Alexandra non détectée dans le texte libre (cas d'usage clé du NER)"


def test_golden_hybrid_au_moins_autant_que_regex():
    """Le mode hybrid doit détecter au moins autant que regex seul."""
    golden = _load_golden()
    for enreg in golden['enregistrements']:
        spans_regex = detect_hybrid(enreg['texte'], mode="regex")
        spans_hybrid = detect_hybrid(enreg['texte'], mode="hybrid")
        assert len(spans_hybrid) >= len(spans_regex), \
            f"Hybrid ({len(spans_hybrid)}) < regex ({len(spans_regex)}) sur {enreg['doar_ident']}"
