"""
Détection PII par regex — production de Spans.
Source : Pseudonymus pseudonymise.py lignes 62-267
Changement de paradigme : les regex ne modifient plus le texte,
elles produisent des Spans sur le texte original.
"""

import re
from dataclasses import dataclass, field


# =============================================================
#  SPAN : unité de détection
# =============================================================

@dataclass
class Span:
    """Une entité détectée dans le texte."""
    start: int
    end: int
    entity_type: str      # "email_txt", "tel_txt", "personne", etc.
    value: str
    score: float = 1.0    # 1.0 pour regex, 0-1 pour NER
    source: str = "regex"
    risk_type: str = "indirect"  # "direct", "finance", "tech", "indirect"


# =============================================================
#  REGEX (reprises intégralement de Pseudonymus)
# =============================================================

# --- Finance et régalien ---
RX_NUM_FISCAL = re.compile(r'\b[0-3]\d{12}\b')
RX_NIR = re.compile(
    r'(?<!\d)([12])[\s.\-]*(\d{2})[\s.\-]*(\d{2})[\s.\-]*'
    r'(\d{2}|2[AB])[\s.\-]*(\d{3})[\s.\-]*(\d{3})'
    r'(?:[\s.\-]*(\d{2}))?(?!\d)', re.IGNORECASE)
RX_IBAN = re.compile(
    r'\b[A-Z]{2}\d{2}[\s\-]?[0-9A-Z]{4}[\s\-]?[0-9A-Z]{4}'
    r'[\s\-]?[0-9A-Z]{4}[\s\-]?[0-9A-Z]{4}'
    r'[\s\-]?[0-9A-Z]{4}[\s\-]?[0-9A-Z]{4}'
    r'[\s\-]?[0-9A-Z]{0,4}[\s\-]?[0-9A-Z]{0,3}\b', re.IGNORECASE)
RX_CB = re.compile(r'\b(?:\d[\s\-]*?){13,19}\b')
RX_CVV = re.compile(r'\b(cvv|cvc|cryptogramme|cv2)\W+(\d{3,4})\b', re.IGNORECASE)
RX_SIRET = re.compile(r'\b\d{3}[\s.]?\d{3}[\s.]?\d{3}(?:[\s.]?\d{5})?\b')

# --- Communication ---
RX_MAILTO = re.compile(r'\b(mailto):([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', re.IGNORECASE)
RX_EMAIL_OBFUSCATED = re.compile(
    r'\b[a-zA-Z0-9_.+-]+\s*(?:@|\[at\]|\(at\)|\[arobase\])'
    r'\s*[a-zA-Z0-9-]+\s*(?:\.|\[dot\]|\(dot\)|point)\s*[a-zA-Z0-9-.]+\b', re.IGNORECASE)
RX_EMAIL_AVEC = re.compile(
    r'\b(De|From|À|A|To|Cc|Bcc)\s*:\s*([A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ\'\-]+(?:\s+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ\'\-]+)*)'
    r'\s*<[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+>', re.IGNORECASE)
RX_EMAIL_ESPACE = re.compile(
    r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\s*\.\s*|\s+|\.)[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-.]+)*')
RX_EMAIL = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# --- Téléphones ---
RX_TEL_FUZZY = re.compile(r'(?<!\d)(?:(?:\+|00)33|0)\s*[1-9](?:[\s._\-]*\d){8}(?!\d)')
RX_TEL_PREFIXE = re.compile(r'TEL\s*:\s*[\d\s.\-]+', re.IGNORECASE)
RX_TEL = re.compile(r'(?<!\d)(?:\+33|0)[1-9](?:[\s.\-]*\d{2}){4}(?!\d)')

# --- URLs ---
RX_URL = re.compile(r'\bhttps?://\S+|\bwww\.\S+')

# --- Organisations ---
RX_ORGA_AGRESSIF = re.compile(
    r'\b([A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ&\'\-]+(?:\s+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ&\'\-]+)*)'
    r'\s+(SA|SAS|SARL|SNC|EURL|SASU|SCI|SCM|SCOP|SEM|GIE|ASSOCIATION|FONDATION)\b')

# --- Adresses ---
RX_VOIE_NUM = re.compile(
    r"\b\d+\s+(?:rue|avenue|boulevard|chemin|impasse|allée|route|bis|ter)"
    r"\s+[A-Za-zÀ-ÖØ-öø-ÿ'\-\s]{3,}", re.IGNORECASE)
RX_VOIE_SANS = re.compile(
    r"\b(?:rue|avenue|boulevard|chemin|impasse|allée|route)"
    r"\s+[A-Za-zÀ-ÖØ-öø-ÿ'\-\s]{3,}", re.IGNORECASE)
RX_CP = re.compile(r'\b\d{5}\b')

# --- Entités personnes ---
RX_SALUTATION = re.compile(
    r'\b(?:Bonjour|Salut|Bonsoir|Hello|Hi|Coucou|Cher|Chère|bonjour|salut|bonsoir|hello|hi|coucou|cher|chère)'
    r'[ \t]+([A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ\'\-]+(?:[ \t]+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ\'\-]+)*)')
RX_TITRE = re.compile(
    r'\b(M\.|Mme\.?|Mlle\.?|[Mm]onsieur|[Mm]adame|[Mm]ademoiselle)\s*'
    r'([A-ZÀ-ÖØ-Ý](?:[a-zà-öø-ÿ]+|[A-ZÀ-ÖØ-Ý]+)[A-Za-zÀ-ÖØ-öø-ÿ\'\-]*'
    r'(?:\s+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ\'\-]+)*)', re.IGNORECASE)
RX_PRENOM_NOM_MAJ = re.compile(
    r'\b([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ\'\-]+)[ ]+'
    r'([A-ZÀ-ÖØ-Ý]{2,}[A-ZÀ-ÖØ-öø-ÿ\'\-]*(?:[ ]+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ\'\-]+)*)')
RX_PRENOM_NOM = re.compile(
    r'\b([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ\'\-]+)(?:[ ]+([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ\'\-]+))+')

# --- Mode fort ---
RX_DATE_NAISS = re.compile(
    r'\b(né|née|naissance)(?:e|s)?\s+(?:le|du|au)?\s*:?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b', re.IGNORECASE)
RX_GPS = re.compile(r'\b-?(?:[1-8]?\d\.\d+|90\.0+)[,\s]+-?(?:1(?:[0-7]\d)|[1-9]?\d)\.\d+\b')
RX_PLAQUE = re.compile(r'\b(?:[A-Z]{2}[-\s]?\d{3}[-\s]?[A-Z]{2}|\d{1,4}[-\s]?[A-Z]{2,3}[-\s]?\d{2})\b')
RX_PRENOM_ISOLE = re.compile(
    r'(?<![A-Za-zÀ-ÖØ-öø-ÿ])([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]*(?:-[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+)*)(?![A-Za-zÀ-ÖØ-öø-ÿ])')
RX_PRENOM_ISOLE_MIN = re.compile(
    r'(?<![A-Za-zÀ-ÖØ-öø-ÿ])([a-zà-öø-ÿ]{3,}(?:-[a-zà-öø-ÿ]{3,})?)(?![A-Za-zÀ-ÖØ-öø-ÿ])')
RX_PREFIXES = re.compile(
    r'\b(BEN|EL|AL|AIT|ABDEL)(?:[\s-][A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ]{2,})+\b', re.IGNORECASE)
RX_MAJ_LONG = re.compile(r"\b(?:[Ll]'|[Dd]')?[A-ZÀ-ÖØ-Ý]{2,}(?:-[A-ZÀ-ÖØ-Ý]{2,})*\b")
RX_VILLE_COMPOSEE = re.compile(
    r"\b[A-ZÀ-ÖØ-Ý]{3,}(?:[\s-](?:SUR|SOUS|LES|AUX|LEZ|LÈZ|DE|DU|D')[\s-][A-ZÀ-ÖØ-Ý]{3,})+\b")

# --- Mode tech (--tech) ---
RX_IPV4 = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
RX_IPV6 = re.compile(
    r'(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}|'
    r'(?:[a-fA-F0-9]{1,4}:){1,7}:|'
    r'::(?:[a-fA-F0-9]{1,4}:){0,5}[a-fA-F0-9]{1,4}')
RX_MAC = re.compile(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b')
RX_JWT = re.compile(r'\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b')
RX_API_KEY = re.compile(r'\b(?:sk|pk|api)_[a-zA-Z0-9]{20,}\b')

# --- Contexte numérique négatif ---
RX_CTX_NB_AVANT = re.compile(
    r'\b(n°|n\.|numéro|décret|article|art\.|référence|ref\.|dossier|commande|lot|page|p\.'
    r'|chapitre|volume|tome|fig\.|figure|tableau|tab\.|kg|g|m|cm|mm|km|€|eur|euros|%|degrés?)\s*$', re.IGNORECASE)
RX_CTX_NB_APRES = re.compile(
    r'^\s*(kg|g|m|cm|mm|km|€|eur|euros|%|degrés?|°|exemplaires?|pages?)', re.IGNORECASE)


# =============================================================
#  VALIDATEURS
# =============================================================

def luhn_check(s: str) -> bool:
    """Validateur Luhn pour CB et SIRET."""
    digits = re.sub(r'\D', '', s)
    if len(digits) < 9:
        return False
    if len(digits) in (9, 14):
        return False
    total = 0
    double = False
    for ch in reversed(digits):
        d = int(ch)
        if double:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        double = not double
    return total % 10 == 0


def luhn_raw(digits: str) -> bool:
    """Validateur Luhn brut (sans nettoyage)."""
    if len(digits) < 9:
        return False
    total = 0
    double = False
    for ch in reversed(digits):
        d = int(ch)
        if double:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        double = not double
    return total % 10 == 0


def nir_check(s: str) -> bool:
    """Validateur NIR (numéro de sécurité sociale)."""
    clean = re.sub(r'[\s.\-]', '', s)
    if len(clean) == 15:
        clean = clean[:13]
    if len(clean) != 13:
        return False
    mois = int(clean[3:5])
    return 1 <= mois <= 12


def siret_check(s: str) -> bool:
    """Validateur SIRET (Luhn sur 9 ou 14 chiffres)."""
    clean = re.sub(r'\D', '', s)
    return len(clean) in (9, 14) and luhn_raw(clean)


def iban_check(s: str) -> bool:
    """Validateur IBAN (mod-97)."""
    clean = re.sub(r'[\s\-]', '', s).upper()
    if len(clean) < 15:
        return False
    rearranged = clean[4:] + clean[:4]
    numeric = ''
    for ch in rearranged:
        if ch.isdigit():
            numeric += ch
        elif ch.isalpha():
            numeric += str(ord(ch) - ord('A') + 10)
        else:
            return False
    try:
        return int(numeric) % 97 == 1
    except ValueError:
        return False


def contexte_nb_negatif(text: str, offset: int, match_len: int) -> bool:
    """Vérifie si un nombre est dans un contexte non personnel (n°, page, €, etc.)."""
    avant = text[max(0, offset - 20):offset]
    if RX_CTX_NB_AVANT.search(avant):
        return True
    apres = text[offset + match_len:min(len(text), offset + match_len + 20)]
    if RX_CTX_NB_APRES.match(apres):
        return True
    return False


# =============================================================
#  DÉTECTION PAR REGEX — production de Spans
# =============================================================

def _detect_simple(text: str, regex, entity_type: str, risk_type: str) -> list[Span]:
    """Détecte par regex sans validateur ni contexte négatif."""
    spans = []
    for m in regex.finditer(text):
        spans.append(Span(
            start=m.start(), end=m.end(),
            entity_type=entity_type, value=m.group(),
            score=1.0, source="regex", risk_type=risk_type,
        ))
    return spans


def _detect_validated(text: str, regex, entity_type: str, risk_type: str,
                      validator) -> list[Span]:
    """Détecte par regex avec validateur (Luhn, NIR, etc.)."""
    spans = []
    for m in regex.finditer(text):
        if validator(m.group()):
            spans.append(Span(
                start=m.start(), end=m.end(),
                entity_type=entity_type, value=m.group(),
                score=1.0, source="regex", risk_type=risk_type,
            ))
    return spans


def _detect_with_ctx(text: str, regex, entity_type: str, risk_type: str,
                     validator=None) -> list[Span]:
    """Détecte par regex avec vérification de contexte négatif."""
    spans = []
    for m in regex.finditer(text):
        if validator and not validator(m.group()):
            continue
        if contexte_nb_negatif(text, m.start(), len(m.group())):
            continue
        spans.append(Span(
            start=m.start(), end=m.end(),
            entity_type=entity_type, value=m.group(),
            score=1.0, source="regex", risk_type=risk_type,
        ))
    return spans


def detect_regex(text: str, fort: bool = False, tech: bool = False) -> list[Span]:
    """Détecte toutes les entités PII par regex dans le texte.

    Retourne une liste de Spans triés par position, sur le texte original
    (pas de modification du texte).
    """
    spans: list[Span] = []

    # --- Finance et régalien ---
    spans.extend(_detect_with_ctx(text, RX_NUM_FISCAL, 'fiscal_txt', 'finance'))
    spans.extend(_detect_validated(text, RX_NIR, 'nir_txt', 'finance', nir_check))
    spans.extend(_detect_validated(text, RX_IBAN, 'iban_txt', 'finance', iban_check))
    spans.extend(_detect_validated(text, RX_CB, 'cb_txt', 'finance', luhn_check))
    spans.extend(_detect_simple(text, RX_CVV, 'cvv_txt', 'finance'))
    spans.extend(_detect_validated(text, RX_SIRET, 'siret_txt', 'indirect', siret_check))

    # --- Communication ---
    spans.extend(_detect_simple(text, RX_MAILTO, 'email_txt', 'direct'))
    spans.extend(_detect_simple(text, RX_EMAIL_OBFUSCATED, 'email_txt', 'direct'))
    spans.extend(_detect_simple(text, RX_EMAIL_AVEC, 'email_txt', 'direct'))
    spans.extend(_detect_simple(text, RX_EMAIL_ESPACE, 'email_txt', 'direct'))
    spans.extend(_detect_simple(text, RX_EMAIL, 'email_txt', 'direct'))

    # --- Téléphones ---
    spans.extend(_detect_simple(text, RX_TEL_FUZZY, 'tel_txt', 'direct'))
    spans.extend(_detect_simple(text, RX_TEL_PREFIXE, 'tel_txt', 'direct'))
    spans.extend(_detect_simple(text, RX_TEL, 'tel_txt', 'direct'))

    # --- URLs ---
    spans.extend(_detect_simple(text, RX_URL, 'url_txt', 'indirect'))

    # --- Organisations ---
    spans.extend(_detect_simple(text, RX_ORGA_AGRESSIF, 'orga_txt', 'indirect'))

    # --- Adresses ---
    spans.extend(_detect_simple(text, RX_VOIE_NUM, 'voie_txt', 'indirect'))
    spans.extend(_detect_simple(text, RX_VOIE_SANS, 'voie_txt', 'indirect'))
    spans.extend(_detect_with_ctx(text, RX_CP, 'cp_txt', 'indirect'))

    # --- Mode fort ---
    if fort:
        spans.extend(_detect_simple(text, RX_DATE_NAISS, 'date_naiss_txt', 'direct'))
        spans.extend(_detect_simple(text, RX_GPS, 'gps_txt', 'indirect'))
        spans.extend(_detect_simple(text, RX_PLAQUE, 'plaque_txt', 'indirect'))
        spans.extend(_detect_simple(text, RX_VILLE_COMPOSEE, 'ville_txt', 'indirect'))
        # Les prénoms isolés et noms propres sont gérés par le detecteur
        # qui a accès aux dictionnaires (pas ici)

    # --- Mode tech ---
    if tech:
        spans.extend(_detect_simple(text, RX_IPV4, 'ipv4_txt', 'tech'))
        spans.extend(_detect_simple(text, RX_IPV6, 'ipv6_txt', 'tech'))
        spans.extend(_detect_simple(text, RX_MAC, 'mac_txt', 'tech'))
        spans.extend(_detect_simple(text, RX_JWT, 'jwt_txt', 'tech'))
        spans.extend(_detect_simple(text, RX_API_KEY, 'api_key_txt', 'tech'))

    # Trier par position et dédupliquer les chevauchements internes
    spans.sort(key=lambda s: (s.start, -s.end))
    return _deduplicate_regex_spans(spans)


def _deduplicate_regex_spans(spans: list[Span]) -> list[Span]:
    """Supprime les doublons parmi les spans regex (même position ou chevauchement).

    Quand plusieurs regex matchent la même zone (ex: RX_EMAIL et RX_EMAIL_ESPACE),
    on garde le span le plus long.
    """
    if not spans:
        return []

    result = [spans[0]]
    for span in spans[1:]:
        dernier = result[-1]
        # Chevauchement ?
        if span.start < dernier.end:
            # Garder le plus long
            if (span.end - span.start) > (dernier.end - dernier.start):
                result[-1] = span
        else:
            result.append(span)
    return result
