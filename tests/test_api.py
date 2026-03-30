"""Tests API FastAPI."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["dictionnaires"]["patronymes"] > 800000
    assert data["dictionnaires"]["prenoms"] > 160000


def test_entity_types():
    r = client.get("/ner/entity-types")
    assert r.status_code == 200
    types = r.json()["types"]
    assert len(types) >= 10
    codes = {t["code"] for t in types}
    assert "personne" in codes
    assert "email_txt" in codes
    assert "iban_txt" in codes


def test_anonymize_basique():
    r = client.post("/ner/anonymize", json={
        "text": "Contact jean.dupont@test.fr ou 06 12 34 56 78",
        "mode": "mask",
        "detection_mode": "regex",
    })
    assert r.status_code == 200
    data = r.json()
    assert "jean.dupont@test.fr" not in data["texte_pseudonymise"]
    assert "[EMAIL_" in data["texte_pseudonymise"]
    assert len(data["correspondances"]) >= 1
    assert data["score"]["total"] > 0


def test_anonymize_mode_anon():
    r = client.post("/ner/anonymize", json={
        "text": "Email jean@test.fr",
        "mode": "anon",
        "detection_mode": "regex",
    })
    assert r.status_code == 200
    assert "***" in r.json()["texte_pseudonymise"]


def test_anonymize_texte_vide_rejete():
    r = client.post("/ner/anonymize", json={
        "text": "",
        "mode": "mask",
    })
    assert r.status_code == 422


def test_extract():
    r = client.post("/ner/extract", json={
        "text": "Contact jean@test.fr ou 06 12 34 56 78",
        "detection_mode": "regex",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 2
    types = {e["type"] for e in data["entities"]}
    assert "email_txt" in types


def test_deanonymize():
    r = client.post("/ner/deanonymize", json={
        "text": "[PERSONNE_1], email [EMAIL_1]",
        "mapping": {
            "[PERSONNE_1]": "Jean Dupont",
            "[EMAIL_1]": "jean@test.fr",
        },
    })
    assert r.status_code == 200
    data = r.json()
    assert data["texte_original"] == "Jean Dupont, email jean@test.fr"
    assert data["remplacements"] == 2


def test_anonymize_whitelist():
    r = client.post("/ner/anonymize", json={
        "text": "Contact Orange au 06 12 34 56 78",
        "mode": "mask",
        "detection_mode": "regex",
        "whitelist": ["Orange"],
    })
    assert r.status_code == 200
    # Orange ne doit pas être masqué
    data = r.json()
    assert "Orange" in data["texte_pseudonymise"] or "orange" in data["texte_pseudonymise"].lower()
