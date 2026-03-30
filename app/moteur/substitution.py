"""
Table de correspondances et substitution par jetons.
Source : Pseudonymus pseudonymise.py lignes 272-349
Adapté pour travailler avec des Spans au lieu de modifier le texte in-place.
"""

import csv
import os
import re
import unicodedata


def normaliser_personne(raw: str) -> str:
    """Normalise un nom pour détecter les doublons."""
    s = raw.strip()
    s = re.sub(r'\[PERSONNE_\d+\]', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(m\.|mme\.?|mlle\.?|monsieur|madame)\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ\-' ]+", ' ', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    parts = s.split(' ')
    if len(parts) == 2 and "'" not in s:
        return ' '.join(sorted(parts))
    return s


class TokenTable:
    """Gestion des jetons de pseudonymisation avec déduplication."""

    PREFIX_MAP = {
        'id': 'ID', 'uuid': 'UUID', 'prenom': 'PRENOM',
        'nom': 'NOM', 'email': 'EMAIL', 'tel': 'TEL',
        'cp': 'CP', 'genre': 'GENRE', 'email_txt': 'EMAIL',
        'tel_txt': 'TEL', 'iban_txt': 'IBAN', 'nir_txt': 'NIR',
        'cb_txt': 'CB', 'cvv_txt': 'CVV', 'siret_txt': 'SIRET',
        'siren_txt': 'SIREN', 'fiscal_txt': 'ID_FISCAL',
        'url_txt': 'URL', 'voie_txt': 'VOIE', 'orga_txt': 'ORGANISATION',
        'ville_txt': 'VILLE', 'date_naiss_txt': 'DATE_NAISSANCE',
        'adresse_txt': 'ADRESSE', 'ip_txt': 'IP',
        'ipv4_txt': 'IPV4', 'ipv6_txt': 'IPV6',
        'mac_txt': 'MAC', 'jwt_txt': 'JWT', 'api_key_txt': 'API_KEY',
        'plaque_txt': 'PLAQUE', 'gps_txt': 'GPS',
        'date_txt': 'DATE', 'montant_txt': 'MONTANT',
        'personne': 'PERSONNE',
    }

    def __init__(self):
        self._counters: dict[str, int] = {}
        self._typed: dict[str, dict[str, tuple[int, str]]] = {}
        self._personnes: dict[str, tuple[str, str]] = {}

    def get_token(self, raw: str) -> str:
        """Jeton PERSONNE_X pour un nom détecté dans le texte."""
        key = normaliser_personne(raw)
        if not key:
            return '[PERSONNE]'
        if key not in self._personnes:
            self._counters['personne'] = self._counters.get('personne', 0) + 1
            pid = f'PERSONNE_{self._counters["personne"]}'
            self._personnes[key] = (pid, raw.strip())
        return f'[{self._personnes[key][0]}]'

    def get_typed_token(self, type_name: str, prefix: str, value) -> str | None:
        """Jeton numéroté [PREFIX_X] pour un champ structuré ou une détection texte."""
        if not value or not str(value).strip():
            return None
        key = str(value).strip().lower()
        if type_name not in self._typed:
            self._typed[type_name] = {}
        if key not in self._typed[type_name]:
            self._counters[type_name] = self._counters.get(type_name, 0) + 1
            self._typed[type_name][key] = (self._counters[type_name], str(value).strip())
        num = self._typed[type_name][key][0]
        return f'[{prefix}_{num}]'

    def get_token_for_span(self, entity_type: str, value: str) -> str:
        """Retourne un jeton pour un Span détecté (par regex ou NER)."""
        prefix = self.PREFIX_MAP.get(entity_type, entity_type.upper())
        if entity_type == 'personne':
            return self.get_token(value)
        token = self.get_typed_token(entity_type, prefix, value)
        return token if token else f'[{prefix}]'

    def export_csv(self, filepath: str, include_source: bool = True):
        """Exporte les correspondances en CSV."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        rows = []
        for type_name, mapping in self._typed.items():
            prefix = self.PREFIX_MAP.get(type_name, type_name.upper())
            for key, (num, original) in mapping.items():
                rows.append((type_name, f'[{prefix}_{num}]', original))
        for key, (pid, original) in self._personnes.items():
            rows.append(('personne', f'[{pid}]', original))
        rows.sort(key=lambda r: (r[0], r[1]))

        header = ['type', 'jeton', 'valeur_originale']
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)
        os.chmod(filepath, 0o600)

    def correspondances_list(self) -> list[dict]:
        """Retourne les correspondances sous forme de liste de dicts (pour l'API)."""
        result = []
        for type_name, mapping in self._typed.items():
            prefix = self.PREFIX_MAP.get(type_name, type_name.upper())
            for key, (num, original) in mapping.items():
                result.append({
                    'type': type_name,
                    'jeton': f'[{prefix}_{num}]',
                    'valeur': original,
                })
        for key, (pid, original) in self._personnes.items():
            result.append({
                'type': 'personne',
                'jeton': f'[{pid}]',
                'valeur': original,
            })
        return sorted(result, key=lambda r: (r['type'], r['jeton']))


def substituer_spans(texte: str, spans: list, tokens: "TokenTable") -> str:
    """Substitue les spans détectés par des jetons dans le texte.

    Les spans doivent être triés par position (start).
    La substitution se fait en ordre inverse pour préserver les positions.
    """
    # Trier par position décroissante
    spans_sorted = sorted(spans, key=lambda s: s.start, reverse=True)
    resultat = texte
    for span in spans_sorted:
        token = tokens.get_token_for_span(span.entity_type, span.value)
        resultat = resultat[:span.start] + token + resultat[span.end:]
    return resultat
