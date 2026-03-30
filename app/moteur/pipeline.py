"""
Pipeline complet de pseudonymisation par enregistrement.
Orchestre : navigation JSON → détection hybride → substitution → scoring.
Source : Pseudonymus pseudonymise.py lignes 965-1093 (refactorisé en spans)
"""

import gc
import json
import re
import uuid

from .detecteur import detect_hybrid
from .navigation import (
    get_path, set_path, get_text_fields,
    unwrap_json_field, rewrap_json_field, resolve_obj_for_path,
)
from .substitution import TokenTable, substituer_spans
from .scoring import RiskScorer, Stats


def process_record(
    record: dict,
    mode: str,
    detection_mode: str = "hybrid",
    fort: bool = False,
    tech: bool = False,
    tokens: TokenTable | None = None,
    stats: Stats | None = None,
    scorer: RiskScorer | None = None,
    mapping: dict | None = None,
) -> dict:
    """Traite un enregistrement JSON (plat ou imbriqué).

    Args:
        record: l'enregistrement à traiter
        mode: "pseudo" (réversible) ou "anon" (irréversible)
        detection_mode: "regex", "ner", ou "hybrid"
        fort: mode fort (prénoms isolés, propagation)
        tech: mode tech (IPv4, MAC, JWT)
        tokens: table de correspondances (partagée entre enregistrements)
        stats: compteurs de traitement
        scorer: scoring RGPD
        mapping: configuration du mapping JSON

    Returns:
        L'enregistrement modifié
    """
    if tokens is None:
        tokens = TokenTable()
    if stats is None:
        stats = Stats()
    if scorer is None:
        scorer = RiskScorer()
    if mapping is None:
        mapping = {}

    champs = mapping.get('champs_sensibles', {})
    texte_libre = mapping.get('texte_libre', [])
    lookup = mapping.get('lookup_noms', {})
    whitelist = set(mapping.get('whitelist', []))
    blacklist = set(mapping.get('blacklist', []))

    # --- Unwrap JSON stringifié si configuré ---
    structure = mapping.get('structure', {})
    unwrap_config = structure.get('unwrap')
    unwrapped = None
    if unwrap_config:
        unwrapped = unwrap_json_field(record, unwrap_config)

    # --- Lookup noms du déclarant ---
    firstname = ''
    lastname = ''
    if lookup:
        fn_path = lookup.get('prenom', '')
        ln_path = lookup.get('nom', '')
        if fn_path:
            obj = resolve_obj_for_path(fn_path, record, unwrapped)
            firstname = get_path(obj, fn_path) or ''
        if ln_path:
            obj = resolve_obj_for_path(ln_path, record, unwrapped)
            lastname = get_path(obj, ln_path) or ''

    # --- Phase 1 : Champs structurés ---
    for field_path, config in champs.items():
        obj = resolve_obj_for_path(field_path, record, unwrapped)
        val = get_path(obj, field_path)
        if val is None or (isinstance(val, str) and not val.strip()):
            continue

        t = config['type']
        prefix = config['jeton']

        if mode == 'pseudo':
            token = tokens.get_typed_token(t, prefix, val)
            stats.add(t, val, token)
            scorer.add('direct' if t in ('nom', 'prenom', 'email', 'tel') else 'indirect')
            set_path(obj, field_path, token)
        else:
            anon_values = {
                'prenom': '***', 'nom': '***',
                'email': 'anonyme@example.com',
                'tel': '00 00 00 00 00',
                'cp': '00000', 'genre': 'Non renseigné',
                'id': stats.counts.get('id', 0) + 1,
                'uuid': str(uuid.uuid4()),
            }
            replacement = anon_values.get(t, '***')
            stats.add(t, val, replacement)
            scorer.add('direct' if t in ('nom', 'prenom', 'email', 'tel') else 'indirect')
            set_path(obj, field_path, replacement)

    # --- Phase 2 : Texte libre ---
    for field_path in texte_libre:
        obj = resolve_obj_for_path(field_path, record, unwrapped)
        text_fields = get_text_fields(obj, field_path)

        for container, key, val in text_fields:
            text = val

            # Lookup direct noms du déclarant dans le texte libre
            if firstname:
                lookup_names = set()
                if firstname.strip():
                    lookup_names.add(firstname.strip())
                if lastname and lastname.strip():
                    lookup_names.add(lastname.strip())
                # Ajouter comme blacklist temporaire pour la détection
                blacklist_augmentee = blacklist | lookup_names
            else:
                blacklist_augmentee = blacklist

            # Détection hybride sur le texte original
            spans = detect_hybrid(
                text,
                mode=detection_mode,
                fort=fort,
                tech=tech,
                whitelist=whitelist,
                blacklist=blacklist_augmentee,
            )

            # Scoring
            for span in spans:
                scorer.add(span.risk_type)
                stats.add(span.entity_type, span.value,
                          tokens.get_token_for_span(span.entity_type, span.value))

            # Substitution
            if mode == 'pseudo':
                text = substituer_spans(text, spans, tokens)
            else:
                # Mode anon : remplacer par ***
                spans_sorted = sorted(spans, key=lambda s: s.start, reverse=True)
                for span in spans_sorted:
                    text = text[:span.start] + '***' + text[span.end:]

            # Écrire la valeur modifiée
            if container is not None and key is not None:
                container[key] = text

    # --- Re-sérialisation unwrap ---
    if unwrap_config and unwrapped is not None:
        rewrap_json_field(record, unwrapped, unwrap_config)

    # --- Nettoyage mémoire (sécurité PII) ---
    gc.collect()

    return record


def process_text(
    text: str,
    mode: str = "pseudo",
    detection_mode: str = "hybrid",
    fort: bool = False,
    tech: bool = False,
    whitelist: set[str] | None = None,
    blacklist: set[str] | None = None,
    tokens: TokenTable | None = None,
    stats: Stats | None = None,
    scorer: RiskScorer | None = None,
) -> dict:
    """Pseudonymise du texte brut (sans mapping, sans structure).

    C'est le scénario A du PRD : texte collé ou document non structuré.

    Returns:
        Dict avec texte_original, texte_pseudonymise, correspondances, stats, score
    """
    if tokens is None:
        tokens = TokenTable()
    if stats is None:
        stats = Stats()
    if scorer is None:
        scorer = RiskScorer()

    # Détection hybride
    spans = detect_hybrid(
        text,
        mode=detection_mode,
        fort=fort,
        tech=tech,
        whitelist=whitelist or set(),
        blacklist=blacklist or set(),
    )

    # Scoring
    for span in spans:
        scorer.add(span.risk_type)
        stats.add(span.entity_type, span.value,
                  tokens.get_token_for_span(span.entity_type, span.value))

    # Substitution
    if mode == 'pseudo':
        texte_anonymise = substituer_spans(text, spans, tokens)
    else:
        texte_anonymise = text
        spans_sorted = sorted(spans, key=lambda s: s.start, reverse=True)
        for span in spans_sorted:
            texte_anonymise = texte_anonymise[:span.start] + '***' + texte_anonymise[span.end:]

    return {
        'texte_original': text,
        'texte_pseudonymise': texte_anonymise,
        'correspondances': tokens.correspondances_list(),
        'stats': stats.to_dict(),
        'score': scorer.to_dict(),
    }
