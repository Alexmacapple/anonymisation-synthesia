"""
Anonymisation-synthesia — API FastAPI locale.
Combine GLiNER2 (NER contextuel) + regex/dictionnaires (Pseudonymus).
"""

import logging
from contextlib import asynccontextmanager

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.models import (
    NERAnonymizeRequest, NERAnonymizeResponse,
    NERExtractRequest, NERExtractResponse,
    NERDeanonymizeRequest, NERDeanonymizeResponse,
    HealthResponse,
)
from .moteur.pipeline import process_text
from .moteur.detecteur import detect_hybrid
from .moteur.ner_gliner import NERService
from .moteur.dictionnaires import Dictionnaires
from .moteur.depseudonymise import depseudonymiser_texte
from .api.routes_fichier import router as fichier_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pré-chargement des modèles au démarrage."""
    # Sécurité : avertissement si DEBUG activé
    if logging.getLogger().level <= logging.DEBUG:
        logger.warning(
            "ATTENTION : le mode DEBUG est activé. "
            "Les logs peuvent contenir des données personnelles (spans, valeurs détectées). "
            "Ne pas utiliser en production."
        )

    logger.info("Chargement des dictionnaires...")
    Dictionnaires.get_instance()

    logger.info("Initialisation du service NER...")
    ner = NERService.get_instance()
    if ner.is_available:
        logger.info("GLiNER2 disponible — mode hybrid activé")
    else:
        logger.warning("GLiNER2 non disponible — mode regex uniquement")

    yield

    logger.info("Arrêt du serveur.")


app = FastAPI(
    title="anonymisation-synthesia",
    version="0.1.0",
    description="API locale d'anonymisation PII — GLiNER2 + regex/dictionnaires",
    lifespan=lifespan,
    # Désactivation des routes /docs et /redoc par défaut. Réimplémentées plus
    # bas avec un openapi_url RELATIF, pour fonctionner aussi bien en accès
    # direct (:7443/docs) qu'à travers le sous-path Tailscale Funnel (/anon/docs).
    docs_url=None,
    redoc_url=None,
)
# Note : pas de root_path ici. Tailscale Funnel sous-path /anon strip le préfixe
# avant de transmettre au backend, et le HTML patché utilise des chemins relatifs.
# root_path="/anon" casserait app.mount("/static", ...) — bug Starlette connu.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fichier_router)

# Fichiers statiques (interface DSFR)
_interface_dir = os.path.join(os.path.dirname(__file__), 'interface')
app.mount("/static", StaticFiles(directory=_interface_dir), name="static")


@app.get("/", include_in_schema=False)
async def index():
    """Sert l'interface web DSFR."""
    return FileResponse(os.path.join(_interface_dir, "index.html"))


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Swagger UI personnalisé avec openapi_url RELATIF.

    Le default FastAPI met url='/openapi.json' (chemin absolu), ce qui casse
    quand l'API est servie sous un sous-path comme /anon/. Avec un chemin
    relatif (openapi.json), le navigateur le résout par rapport au document
    courant, donc :
    - https://...net:7443/docs       → /openapi.json     ✓
    - https://...net/anon/docs       → /anon/openapi.json ✓
    """
    return get_swagger_ui_html(
        openapi_url="openapi.json",
        title="anonymisation-synthesia - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """ReDoc personnalisé avec openapi_url RELATIF — même raison que /docs."""
    return get_redoc_html(
        openapi_url="openapi.json",
        title="anonymisation-synthesia - ReDoc",
    )


# =============================================================
#  ROUTES MVP
# =============================================================

@app.post("/ner/anonymize", response_model=NERAnonymizeResponse)
async def anonymize(request: NERAnonymizeRequest):
    """Anonymise du texte brut. Route principale du MVP."""
    mode_pseudo = "pseudo" if request.mode == "mask" else "anon"

    result = process_text(
        text=request.text,
        mode=mode_pseudo,
        detection_mode=request.detection_mode,
        fort=request.fort,
        tech=request.tech,
        whitelist=set(request.whitelist),
        blacklist=set(request.blacklist),
    )

    return NERAnonymizeResponse(**result)


@app.post("/ner/extract", response_model=NERExtractResponse)
async def extract(request: NERExtractRequest):
    """Extraction d'entités sans anonymisation."""
    spans = detect_hybrid(
        text=request.text,
        mode=request.detection_mode,
        fort=request.fort,
        tech=request.tech,
    )

    entities = [
        {
            "text": s.value,
            "type": s.entity_type,
            "start": s.start,
            "end": s.end,
            "score": s.score,
            "source": s.source,
            "risk_type": s.risk_type,
        }
        for s in spans
    ]

    return NERExtractResponse(
        entities=entities,
        count=len(entities),
        detection_mode=request.detection_mode,
    )


@app.post("/ner/deanonymize", response_model=NERDeanonymizeResponse)
async def deanonymize(request: NERDeanonymizeRequest):
    """Restaure un texte anonymisé avec le mapping."""
    texte_restaure, count = depseudonymiser_texte(request.text, request.mapping)
    return NERDeanonymizeResponse(
        texte_original=texte_restaure,
        remplacements=count,
    )


@app.get("/ner/entity-types")
async def entity_types():
    """Liste des types d'entités supportés."""
    return {
        "types": [
            {"code": "personne", "label": "Personnes", "category": "direct"},
            {"code": "email_txt", "label": "Emails", "category": "direct"},
            {"code": "tel_txt", "label": "Téléphones", "category": "direct"},
            {"code": "adresse_txt", "label": "Adresses", "category": "indirect"},
            {"code": "iban_txt", "label": "IBAN", "category": "finance"},
            {"code": "nir_txt", "label": "N° Sécu. sociale", "category": "finance"},
            {"code": "cb_txt", "label": "Carte bancaire", "category": "finance"},
            {"code": "ip_txt", "label": "Adresse IP", "category": "tech"},
            {"code": "date_naiss_txt", "label": "Date de naissance", "category": "direct"},
            {"code": "orga_txt", "label": "Organisations", "category": "indirect"},
            {"code": "ville_txt", "label": "Lieux", "category": "indirect"},
            {"code": "siret_txt", "label": "SIRET/SIREN", "category": "indirect"},
            {"code": "url_txt", "label": "URLs", "category": "indirect"},
            {"code": "voie_txt", "label": "Adresses postales", "category": "indirect"},
            {"code": "cp_txt", "label": "Codes postaux", "category": "indirect"},
        ]
    }


@app.post("/ner/compare")
async def compare(request: NERExtractRequest):
    """Compare les résultats regex vs NER vs hybrid sur le même texte."""
    from .moteur.regex import detect_regex as _detect_regex
    from .moteur.substitution import TokenTable, substituer_spans

    spans_regex = _detect_regex(request.text, fort=request.fort, tech=request.tech)
    ner = NERService.get_instance()
    spans_ner = ner.extract(request.text, threshold=request.threshold) if ner.is_available else []
    spans_hybrid = detect_hybrid(request.text, mode="hybrid", fort=request.fort, tech=request.tech)

    def _spans_to_list(spans):
        return [{"text": s.value, "type": s.entity_type, "source": s.source, "score": s.score} for s in spans]

    # Générer les 6 rendus anonymisés
    tokens_r = TokenTable()
    rendu_regex = substituer_spans(request.text, spans_regex, tokens_r)

    spans_regex_fort = _detect_regex(request.text, fort=True, tech=False)
    tokens_rf = TokenTable()
    rendu_regex_fort = substituer_spans(request.text, spans_regex_fort, tokens_rf)

    spans_regex_fort_tech = _detect_regex(request.text, fort=True, tech=True)
    tokens_rft = TokenTable()
    rendu_regex_fort_tech = substituer_spans(request.text, spans_regex_fort_tech, tokens_rft)

    tokens_n = TokenTable()
    rendu_ner = substituer_spans(request.text, spans_ner, tokens_n)

    tokens_h = TokenTable()
    rendu_hybrid = substituer_spans(request.text, spans_hybrid, tokens_h)

    spans_hybrid_ft = detect_hybrid(request.text, mode="hybrid", fort=True, tech=True)
    tokens_hft = TokenTable()
    rendu_hybrid_fort_tech = substituer_spans(request.text, spans_hybrid_ft, tokens_hft)

    regex_types = {s.value for s in spans_regex}
    ner_types = {s.value for s in spans_ner}

    return {
        "regex_only": _spans_to_list(spans_regex),
        "ner_only": _spans_to_list(spans_ner),
        "hybrid": _spans_to_list(spans_hybrid),
        "rendu_regex": rendu_regex,
        "rendu_regex_fort": rendu_regex_fort,
        "rendu_regex_fort_tech": rendu_regex_fort_tech,
        "rendu_ner": rendu_ner,
        "rendu_hybrid": rendu_hybrid,
        "rendu_hybrid_fort_tech": rendu_hybrid_fort_tech,
        "diagnostic": {
            "regex_seul": len(spans_regex),
            "ner_seul": len(spans_ner),
            "hybrid": len(spans_hybrid),
            "apport_ner": [s.value for s in spans_ner if s.value not in regex_types],
            "apport_regex": [s.value for s in spans_regex if s.value not in ner_types],
        },
    }


@app.post("/ner/validate")
async def validate(request: NERAnonymizeRequest):
    """Vérifie qu'un texte anonymisé ne contient plus de PII détectable."""
    spans = detect_hybrid(request.text, mode="hybrid", fort=True, tech=True)
    fuites = [
        {"text": s.value, "type": s.entity_type, "score": s.score,
         "message": f"{s.entity_type} non masqué"}
        for s in spans
        if not s.value.startswith('[') or not s.value.endswith(']')
    ]
    return {
        "clean": len(fuites) == 0,
        "fuites": fuites,
    }


@app.post("/mapping/generate")
async def mapping_generate(path: str):
    """Génère un mapping squelette depuis un fichier."""
    import json as _json
    from .formats.base import load_file, detect_format

    if not os.path.exists(path):
        from fastapi import HTTPException
        raise HTTPException(404, f"Fichier non trouvé : {path}")

    ext = detect_format(path)
    if ext == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        sample = data[0] if isinstance(data, list) and data else data
    else:
        data = load_file(path, {})
        sample = data[0] if data else {}

    mapping = {
        "description": f"Mapping automatique pour {os.path.basename(path)}",
        "champs_sensibles": {},
        "texte_libre": [],
        "lookup_noms": {},
        "whitelist": [],
        "blacklist": [],
    }

    type_hints = {
        'nom': ['nom', 'name', 'lastname', 'surname'],
        'prenom': ['prenom', 'firstname', 'given'],
        'email': ['email', 'mail', 'courriel'],
        'tel': ['tel', 'phone', 'telephone', 'mobile'],
        'cp': ['cp', 'postal', 'zip', 'code_postal'],
        'id': ['id', 'ident', 'identifiant'],
    }

    if isinstance(sample, dict):
        for key, value in sample.items():
            key_lower = key.lower()
            detected = False
            for type_name, hints in type_hints.items():
                if any(h in key_lower for h in hints):
                    mapping['champs_sensibles'][key] = {'type': type_name, 'jeton': type_name.upper()}
                    detected = True
                    break
            if not detected and isinstance(value, str) and len(value) > 50:
                mapping['texte_libre'].append(key)

    return mapping


@app.post("/mapping/validate")
async def mapping_validate(mapping: dict, path: str | None = None):
    """Valide un mapping JSON et vérifie la cohérence avec un fichier."""
    erreurs = []
    avertissements = []

    # Vérifications structurelles
    if 'champs_sensibles' not in mapping and 'texte_libre' not in mapping:
        erreurs.append("Le mapping doit contenir au moins 'champs_sensibles' ou 'texte_libre'")

    types_valides = {'nom', 'prenom', 'email', 'tel', 'cp', 'id', 'uuid', 'genre', 'iban', 'nir', 'cb', 'cvv', 'siret', 'siren'}
    for champ, config in mapping.get('champs_sensibles', {}).items():
        if 'type' not in config:
            erreurs.append(f"Champ '{champ}' : 'type' manquant")
        elif config['type'] not in types_valides:
            avertissements.append(f"Champ '{champ}' : type '{config['type']}' non standard (valides : {', '.join(sorted(types_valides))})")
        if 'jeton' not in config:
            erreurs.append(f"Champ '{champ}' : 'jeton' manquant")

    # Vérification avec le fichier si fourni
    champs_absents = []
    if path and os.path.exists(path):
        import json as _json
        from .formats.base import load_file, detect_format
        ext = detect_format(path)
        if ext == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            sample = data[0] if isinstance(data, list) and data else data
        else:
            data = load_file(path, {})
            sample = data[0] if data else {}

        if isinstance(sample, dict):
            cles_fichier = set(sample.keys())
            for champ in mapping.get('champs_sensibles', {}):
                racine = champ.split('.')[0]
                if racine not in cles_fichier:
                    champs_absents.append(champ)
            for champ in mapping.get('texte_libre', []):
                racine = champ.split('.')[0].split('[')[0]
                if racine not in cles_fichier:
                    champs_absents.append(champ)

    if champs_absents:
        avertissements.append(f"Champs absents du fichier : {', '.join(champs_absents)}")

    return {
        "valide": len(erreurs) == 0,
        "erreurs": erreurs,
        "avertissements": avertissements,
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """État du service."""
    ner = NERService.get_instance()
    dicos = Dictionnaires.get_instance()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        ner=ner.info(),
        dictionnaires={
            "patronymes": len(dicos.patronymes),
            "prenoms": len(dicos.prenoms),
        },
    )


@app.get("/health/stats")
async def health_stats():
    """Statistiques détaillées des dictionnaires chargés."""
    dicos = Dictionnaires.get_instance()
    return {
        "dictionnaires": {
            "patronymes": len(dicos.patronymes),
            "prenoms": len(dicos.prenoms),
            "stopwords_capitalises": len(dicos.stopwords_cap),
            "stopwords_minuscules": len(dicos.stopwords_min),
            "majuscules_garder": len(dicos.majuscules_garder),
            "villes_france": len(dicos.villes_france),
            "mots_organisations": len(dicos.mots_organisations),
            "contexte_institution": len(dicos.contexte_institution),
            "acronymes_garder": len(dicos.acronymes_garder),
        }
    }
