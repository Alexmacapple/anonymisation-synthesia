"""
Chargement des données de référence (dictionnaires).
Source : Pseudonymus pseudonymise.py lignes 33-55
"""

import json
import os
import sys
import unicodedata


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_SCRIPT_DIR, '..', '..', 'data')


def _load_set(filename: str) -> set[str]:
    """Charge un fichier JSON en set de strings."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return set(json.load(f))


def _load_set_upper(filename: str) -> set[str]:
    """Charge un fichier JSON en set de strings UPPERCASE."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return set(x.upper() for x in json.load(f))


class Dictionnaires:
    """Singleton contenant tous les dictionnaires de référence."""

    _instance = None

    def __init__(self):
        self.patronymes: set[str] = set()
        self.prenoms: set[str] = set()
        self.stopwords_cap: set[str] = set()
        self.stopwords_min: set[str] = set()
        self.majuscules_garder: set[str] = set()
        self.villes_france: set[str] = set()
        self.mots_organisations: set[str] = set()
        self.contexte_institution: set[str] = set()
        self.acronymes_garder: set[str] = set()
        self._loaded = False

    @classmethod
    def get_instance(cls) -> "Dictionnaires":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.charger()
        return cls._instance

    def charger(self):
        """Charge tous les dictionnaires depuis le répertoire data/."""
        if self._loaded:
            return
        print('Chargement des données de référence...', file=sys.stderr)
        self.patronymes = _load_set_upper('noms.json')
        self.prenoms = _load_set_upper('prenoms.json')
        self.stopwords_cap = _load_set('stopwords-capitalises.json')
        self.stopwords_min = _load_set('stopwords-minuscules.json')
        self.majuscules_garder = _load_set('majuscules-garder.json')
        self.villes_france = _load_set('villes-france.json')
        self.mots_organisations = _load_set('mots-organisations.json')
        self.contexte_institution = _load_set('contexte-institution.json')
        self.acronymes_garder = _load_set('acronymes-garder.json')
        self._loaded = True
        print(f'  {len(self.patronymes)} patronymes, {len(self.prenoms)} prénoms chargés.', file=sys.stderr)

    def est_prenom_connu(self, mot: str) -> bool:
        """Vérifie si un mot est un prénom connu."""
        if not mot or len(mot) < 2:
            return False
        key = mot.upper().strip()
        if key in self.prenoms:
            return True
        sans_accent = unicodedata.normalize('NFD', mot).encode('ascii', 'ignore').decode('ascii')
        return sans_accent.upper().strip() in self.prenoms

    def est_patronyme_connu(self, mot: str) -> bool:
        """Vérifie si un mot est un patronyme connu."""
        if not mot or len(mot) < 2:
            return False
        return mot.upper().strip() in self.patronymes

    def est_stopword(self, mot: str) -> bool:
        """Vérifie si un mot est dans les stopwords (capitalisés ou minuscules)."""
        return mot in self.stopwords_cap or mot.lower() in self.stopwords_min

    def est_acronyme_garder(self, mot: str) -> bool:
        """Vérifie si un mot est un acronyme à préserver."""
        return mot in self.acronymes_garder or mot.upper() in self.majuscules_garder
