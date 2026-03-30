"""
Détecteur hybride — orchestre regex et NER, fusionne les spans.
C'est le composant central du projet.

Architecture :
    texte original
        ├── regex.detect_regex(texte) → spans_regex
        ├── ner.extract(texte)        → spans_ner
        └── fusion(spans_regex, spans_ner) → spans_unifiés
                └── filtrage whitelist
                └── validation dictionnaires
"""

import logging

from .regex import Span, detect_regex
from .ner_gliner import NERService
from .dictionnaires import Dictionnaires

logger = logging.getLogger(__name__)

# Types financiers : regex toujours prioritaire (validateurs mathématiques)
TYPES_FINANCE = {'iban_txt', 'nir_txt', 'cb_txt', 'cvv_txt', 'siret_txt', 'fiscal_txt'}


def _spans_overlap(a: Span, b: Span) -> bool:
    """Vérifie si deux spans se chevauchent."""
    return a.start < b.end and b.start < a.end


def _resolve_overlap(a: Span, b: Span) -> Span:
    """Résout un chevauchement entre deux spans.

    Règles de priorité :
    1. Regex finance > tout (validateurs mathématiques)
    2. NER > regex heuristique (noms ambigus)
    3. En cas d'égalité, garder le span le plus long
    """
    # Regex finance toujours prioritaire
    if a.entity_type in TYPES_FINANCE and a.source == "regex":
        return a
    if b.entity_type in TYPES_FINANCE and b.source == "regex":
        return b

    # NER prioritaire sur regex heuristique
    if a.source == "ner" and b.source == "regex" and b.entity_type not in TYPES_FINANCE:
        return a
    if b.source == "ner" and a.source == "regex" and a.entity_type not in TYPES_FINANCE:
        return b

    # Garder le plus long
    len_a = a.end - a.start
    len_b = b.end - b.start
    return a if len_a >= len_b else b


def _fusionner_spans(spans_regex: list[Span], spans_ner: list[Span]) -> list[Span]:
    """Fusionne deux listes de spans en résolvant les chevauchements."""
    tous = spans_regex + spans_ner
    if not tous:
        return []

    # Trier par position
    tous.sort(key=lambda s: (s.start, -s.end))

    # Résoudre les chevauchements
    resultat = [tous[0]]
    for span in tous[1:]:
        dernier = resultat[-1]
        if _spans_overlap(dernier, span):
            # Chevauchement — résoudre
            gagnant = _resolve_overlap(dernier, span)
            resultat[-1] = gagnant
        else:
            resultat.append(span)

    return resultat


def _filtrer_whitelist(spans: list[Span], whitelist: set[str]) -> list[Span]:
    """Retire les spans dont la valeur est dans la whitelist."""
    if not whitelist:
        return spans
    whitelist_upper = {w.upper() for w in whitelist}
    return [s for s in spans if s.value.upper() not in whitelist_upper]


def _filtrer_blacklist(spans: list[Span], blacklist: set[str],
                       text: str) -> list[Span]:
    """Ajoute des spans pour les mots de la blacklist non encore détectés."""
    if not blacklist:
        return spans

    # Positions déjà couvertes
    couvert = set()
    for s in spans:
        couvert.update(range(s.start, s.end))

    nouveaux = list(spans)
    import re
    for mot in blacklist:
        for m in re.finditer(re.escape(mot), text, re.IGNORECASE):
            if m.start() not in couvert:
                nouveaux.append(Span(
                    start=m.start(), end=m.end(),
                    entity_type='personne', value=m.group(),
                    score=1.0, source='blacklist', risk_type='direct',
                ))

    nouveaux.sort(key=lambda s: (s.start, -s.end))
    return nouveaux


def _valider_ner_par_dictionnaires(spans: list[Span], dicos: Dictionnaires) -> list[Span]:
    """Filtre les faux positifs NER en utilisant les dictionnaires.

    Rejette les détections NER de type "personne" avec score < 0.7
    qui ne sont pas dans les dictionnaires de noms/prénoms.
    """
    valides = []
    for span in spans:
        if (span.source == "ner"
                and span.entity_type == "personne"
                and span.score < 0.7):
            # Vérifier dans les dictionnaires
            mots = span.value.split()
            connu = any(
                dicos.est_prenom_connu(m) or dicos.est_patronyme_connu(m)
                for m in mots
            )
            if not connu:
                logger.warning(
                    f"Entité NER rejetée par validation dictionnaire "
                    f"(type={span.entity_type}, score={span.score:.2f}, value='{span.value}')"
                )
                continue
        valides.append(span)
    return valides


def detect_hybrid(
    text: str,
    mode: str = "hybrid",
    fort: bool = False,
    tech: bool = False,
    whitelist: set[str] | None = None,
    blacklist: set[str] | None = None,
    ner_labels: list[str] | None = None,
    ner_threshold: float = 0.4,
) -> list[Span]:
    """Détecte les entités PII dans le texte.

    Les deux moteurs tournent sur le texte ORIGINAL, indépendamment.
    Les spans sont fusionnés après, puis filtrés.

    Args:
        text: texte à analyser
        mode: "regex", "ner", ou "hybrid"
        fort: active le mode fort (prénoms isolés, propagation, etc.)
        tech: active la détection technique (IPv4, MAC, JWT, etc.)
        whitelist: mots à ne jamais pseudonymiser
        blacklist: mots à toujours pseudonymiser
        ner_labels: labels NER personnalisés
        ner_threshold: seuil de confiance NER

    Returns:
        Liste de Spans triés par position, sans chevauchements
    """
    spans_regex = []
    spans_ner = []

    # --- Détection regex (sur le texte original) ---
    if mode in ("regex", "hybrid"):
        spans_regex = detect_regex(text, fort=fort, tech=tech)
        logger.info(f"Regex : {len(spans_regex)} spans détectés")

    # --- Détection NER (sur le texte original) ---
    if mode in ("ner", "hybrid"):
        ner = NERService.get_instance()
        if ner.is_available:
            try:
                spans_ner = ner.extract(text, labels=ner_labels, threshold=ner_threshold)
                logger.info(f"NER : {len(spans_ner)} spans détectés")
            except Exception as e:
                logger.error(f"Erreur NER, fallback regex : {e}")
                spans_ner = []
        elif mode == "ner":
            logger.warning("NER demandé mais GLiNER2 non disponible. Aucune détection.")
        else:
            logger.info("GLiNER2 non disponible, mode hybrid dégradé en regex seul")

    # --- Fusion ---
    if mode == "regex":
        spans = spans_regex
    elif mode == "ner":
        spans = spans_ner
    else:
        spans = _fusionner_spans(spans_regex, spans_ner)
        logger.info(f"Fusion : {len(spans)} spans après résolution des chevauchements")

    # --- Validation NER par dictionnaires ---
    dicos = Dictionnaires.get_instance()
    spans = _valider_ner_par_dictionnaires(spans, dicos)

    # --- Filtrage whitelist/blacklist ---
    spans = _filtrer_whitelist(spans, whitelist or set())
    spans = _filtrer_blacklist(spans, blacklist or set(), text)

    return spans
