"""Tests des formats de fichiers."""

import json
import os
import sys
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.formats.base import load_file, save_file, detect_format


def test_detect_format_json():
    assert detect_format("test.json") == ".json"

def test_detect_format_csv():
    assert detect_format("test.csv") == ".csv"

def test_detect_format_xlsx():
    assert detect_format("test.xlsx") == ".xlsx"

def test_detect_format_docx():
    assert detect_format("test.docx") == ".docx"

def test_detect_format_pdf():
    assert detect_format("test.pdf") == ".pdf"

def test_detect_format_txt():
    assert detect_format("test.txt") == ".txt"

def test_detect_format_md():
    assert detect_format("notes.md") == ".md"


def test_load_json():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump([{"nom": "Dupont", "email": "a@b.fr"}], f)
        path = f.name
    try:
        data = load_file(path, {})
        assert len(data) == 1
        assert data[0]["nom"] == "Dupont"
    finally:
        os.unlink(path)


def test_load_csv():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write("nom,email\nDupont,a@b.fr\nMartin,c@d.fr\n")
        path = f.name
    try:
        data = load_file(path, {})
        assert len(data) == 2
        assert data[0]["nom"] == "Dupont"
    finally:
        os.unlink(path)


def test_load_txt():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("Bonjour Jean Dupont, email jean@test.fr")
        path = f.name
    try:
        data = load_file(path, {})
        assert len(data) == 1
        assert "Jean Dupont" in data[0]["texte"]
    finally:
        os.unlink(path)


def test_save_json():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        path = f.name
    try:
        data = [{"nom": "[NOM_1]", "email": "[EMAIL_1]"}]
        output = save_file(data, path, '_PSEUDO', {})
        assert output.endswith('_PSEUDO.json')
        with open(output, 'r', encoding='utf-8') as f:
            result = json.load(f)
        assert result[0]["nom"] == "[NOM_1]"
    finally:
        os.unlink(path)
        if os.path.exists(output):
            os.unlink(output)


def test_save_csv():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write("nom,email\nDupont,a@b.fr\n")
        path = f.name
    try:
        data = [{"nom": "[NOM_1]", "email": "[EMAIL_1]"}]
        output = save_file(data, path, '_PSEUDO', {})
        assert output.endswith('_PSEUDO.csv')
        assert os.path.exists(output)
    finally:
        os.unlink(path)
        if os.path.exists(output):
            os.unlink(output)
