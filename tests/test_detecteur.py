"""Tests du détecteur hybride."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.moteur.detecteur import detect_hybrid


def test_hybrid_detecte_email():
    spans = detect_hybrid("Contact jean@test.fr", mode="hybrid")
    assert any(s.entity_type == 'email_txt' for s in spans)


def test_hybrid_detecte_tel():
    spans = detect_hybrid("Appelez le 06 12 34 56 78", mode="hybrid")
    assert any(s.entity_type == 'tel_txt' for s in spans)


def test_regex_seul():
    spans = detect_hybrid("jean@test.fr", mode="regex")
    assert all(s.source == "regex" for s in spans)


def test_whitelist_filtre():
    spans = detect_hybrid("Contact Orange", mode="regex", whitelist={"Orange"})
    assert all(s.value.upper() != "ORANGE" for s in spans)


def test_blacklist_ajoute():
    spans = detect_hybrid("Contactez Dupont", mode="regex", blacklist={"Dupont"})
    assert any(s.value == "Dupont" for s in spans)


def test_mode_fort_date_naissance():
    spans = detect_hybrid("née le 12/04/1985", mode="regex", fort=True)
    assert any(s.entity_type == 'date_naiss_txt' for s in spans)


def test_mode_tech_ipv4():
    spans = detect_hybrid("IP: 192.168.1.1", mode="regex", tech=True)
    assert any(s.entity_type == 'ipv4_txt' for s in spans)


def test_pas_de_chevauchement():
    spans = detect_hybrid("jean@test.fr et 06 12 34 56 78", mode="hybrid")
    for i in range(len(spans) - 1):
        assert spans[i].end <= spans[i+1].start, \
            f"Chevauchement : {spans[i]} et {spans[i+1]}"


def test_spans_tries():
    spans = detect_hybrid("jean@test.fr puis 06 12 34 56 78", mode="hybrid")
    for i in range(len(spans) - 1):
        assert spans[i].start <= spans[i+1].start
