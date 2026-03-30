"""
Navigation JSON : notation pointée, unwrap JSON stringifié, arrays.
Source : Pseudonymus pseudonymise.py lignes 896-953
"""

import json


def get_path(obj: dict, path: str):
    """Lit une valeur via notation pointée (ex: 'Report.Firstname'). Retourne None si introuvable."""
    parts = path.split('.')
    current = obj
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def set_path(obj: dict, path: str, value):
    """Écrit une valeur via notation pointée. Crée les clés intermédiaires."""
    parts = path.split('.')
    current = obj
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def get_text_fields(obj: dict, path: str) -> list[tuple[dict | None, str | None, str]]:
    """Retourne une liste de (conteneur, clé, valeur) pour un chemin.

    Supporte la notation avec arrays : 'Details[].Value'
    """
    if '[]' in path:
        before, after = path.split('[]', 1)
        after = after.lstrip('.')
        array = get_path(obj, before)
        if not array or not isinstance(array, list):
            return []
        results = []
        for item in array:
            if after:
                val = get_path(item, after)
                if val and isinstance(val, str):
                    after_parts = after.split('.')
                    container = item
                    for p in after_parts[:-1]:
                        container = container.get(p, {})
                    results.append((container, after_parts[-1], val))
            elif isinstance(item, str):
                results.append((None, None, item))
        return results
    else:
        val = get_path(obj, path)
        if val and isinstance(val, str):
            parts = path.split('.')
            container = obj
            for p in parts[:-1]:
                container = container.get(p, {})
            return [(container, parts[-1], val)]
        return []


def unwrap_json_field(record: dict, unwrap_config: dict) -> dict | None:
    """Dépaquette un champ JSON stringifié.

    Args:
        record: l'enregistrement contenant le champ
        unwrap_config: {'field': 'RCLMFicheReportJsonSC', 'parse': 'json_string'}

    Returns:
        L'objet JSON dépaqueté, ou None si échec
    """
    field = unwrap_config.get('field', '')
    raw = record.get(field, '')
    if raw and isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def rewrap_json_field(record: dict, unwrapped: dict, unwrap_config: dict):
    """Re-sérialise l'objet dépaqueté dans le champ d'origine."""
    field = unwrap_config.get('field', '')
    record[field] = json.dumps(unwrapped, ensure_ascii=False)


def resolve_obj_for_path(path: str, record: dict, unwrapped: dict | None) -> dict:
    """Retourne l'objet racine approprié pour un chemin donné.

    Si le chemin commence par une clé de l'objet unwrappé, naviguer dedans.
    """
    if unwrapped and '.' in path:
        first_part = path.split('.')[0]
        if isinstance(unwrapped, dict) and first_part in unwrapped:
            return unwrapped
    return record


def load_mapping(path: str) -> dict:
    """Charge un fichier de mapping JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
