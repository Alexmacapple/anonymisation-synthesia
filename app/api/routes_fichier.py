"""Routes pour le traitement de fichiers complets."""

import atexit
import copy
import gc
import json
import logging
import os
import tempfile
import time

import asyncio
import uuid as _uuid

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from ..moteur.pipeline import process_record, process_text
from ..moteur.substitution import TokenTable
from ..moteur.scoring import RiskScorer, Stats
from ..moteur.navigation import load_mapping
from ..formats.base import load_file, save_file, detect_format
from ..config import CONFIDENTIEL_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fichier", tags=["fichier"])

# Registre des fichiers temporaires à nettoyer
_temp_files: list[str] = []


def _cleanup_temp_files():
    """Supprime les fichiers temporaires au shutdown."""
    for f in _temp_files:
        try:
            if os.path.exists(f):
                os.unlink(f)
                logger.info(f"Fichier temporaire supprimé : {f}")
        except OSError:
            pass
    _temp_files.clear()


atexit.register(_cleanup_temp_files)


class FichierAnonymiseRequest(BaseModel):
    path: str = Field(..., description="Chemin du fichier à traiter")
    mapping_path: str | None = Field(None, description="Chemin du mapping JSON (optionnel)")
    mapping: dict | None = Field(None, description="Mapping inline (optionnel)")
    mode: str = Field(default="pseudo", pattern="^(pseudo|anon)$")
    detection_mode: str = Field(default="hybrid", pattern="^(regex|ner|hybrid)$")
    fort: bool = False
    tech: bool = False
    dry_run: bool = False
    limit: int | None = Field(None, description="Nombre max d'enregistrements (None = tous)")


class FichierAnonymiseResponse(BaseModel):
    output_path: str | None
    csv_path: str | None
    total: int
    traites: int
    remplacements: int
    score_moyen: float
    niveau: str
    duree_s: float
    correspondances: int


@router.post("/anonymise", response_model=FichierAnonymiseResponse)
async def anonymiser_fichier(request: FichierAnonymiseRequest):
    """Anonymise un fichier complet (multi-format)."""

    if not os.path.exists(request.path):
        raise HTTPException(404, f"Fichier non trouvé : {request.path}")

    # Charger le mapping
    mapping = request.mapping or {}
    if request.mapping_path:
        mapping = load_mapping(request.mapping_path)

    # Charger le fichier
    t0 = time.time()
    ext = detect_format(request.path)

    if ext == '.json':
        with open(request.path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
    else:
        data = load_file(request.path, mapping)

    total = len(data)

    # Limiter si demandé
    if request.limit:
        data = data[:request.limit]
    if request.dry_run:
        data = data[:100]

    # Traitement
    tokens = TokenTable()
    stats = Stats()
    scorer = RiskScorer()

    has_mapping = bool(mapping.get('champs_sensibles') or mapping.get('texte_libre'))

    for i, record in enumerate(data):
        try:
            if has_mapping:
                record_copy = copy.deepcopy(record)
                process_record(
                    record_copy, mode=request.mode, detection_mode=request.detection_mode,
                    fort=request.fort, tech=request.tech,
                    tokens=tokens, stats=stats, scorer=scorer, mapping=mapping,
                )
                data[i] = record_copy
            else:
                if isinstance(record, dict):
                    for key, val in record.items():
                        if not isinstance(val, str) or not val.strip():
                            continue
                        result = process_text(
                            val, mode=request.mode, detection_mode=request.detection_mode,
                            fort=request.fort, tech=request.tech,
                            tokens=tokens, stats=stats, scorer=scorer,
                        )
                        record[key] = result['texte_pseudonymise']
                else:
                    texte = str(record)
                    if texte:
                        result = process_text(
                            texte, mode=request.mode, detection_mode=request.detection_mode,
                            fort=request.fort, tech=request.tech,
                            tokens=tokens, stats=stats, scorer=scorer,
                        )
        except Exception as e:
            logger.error(f"Erreur enregistrement {i} : {e}")
            stats.errors += 1

    duree = time.time() - t0

    # Nettoyage mémoire (sécurité PII)
    gc.collect()

    # Sauvegarder
    output_path = None
    csv_path = None

    if not request.dry_run:
        output_path = save_file(data, request.path, '_PSEUDO', mapping)
        os.makedirs(CONFIDENTIEL_DIR, exist_ok=True)
        csv_path = os.path.join(CONFIDENTIEL_DIR, 'correspondances.csv')
        tokens.export_csv(csv_path)

    return FichierAnonymiseResponse(
        output_path=output_path,
        csv_path=csv_path,
        total=total,
        traites=len(data),
        remplacements=stats.total_remplacements(),
        score_moyen=scorer.score / max(len(data), 1),
        niveau=scorer.level(),
        duree_s=round(duree, 1),
        correspondances=len(tokens.correspondances_list()),
    )


# =============================================================
#  Routes catalogue P2
# =============================================================

class FichierScoreRequest(BaseModel):
    path: str
    mapping_path: str | None = None
    mapping: dict | None = None
    detection_mode: str = Field(default="hybrid", pattern="^(regex|ner|hybrid)$")
    fort: bool = False
    tech: bool = False
    limit: int = Field(default=100, ge=1, le=10000)


@router.post("/score")
async def scorer_fichier(request: FichierScoreRequest):
    """Scoring RGPD par enregistrement sans anonymiser."""
    if not os.path.exists(request.path):
        raise HTTPException(404, f"Fichier non trouvé : {request.path}")

    mapping = request.mapping or {}
    if request.mapping_path:
        mapping = load_mapping(request.mapping_path)

    ext = detect_format(request.path)
    if ext == '.json':
        with open(request.path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
    else:
        data = load_file(request.path, mapping)

    total = len(data)
    data = data[:request.limit]

    has_mapping = bool(mapping.get('champs_sensibles') or mapping.get('texte_libre'))
    scores = []

    for record in data:
        scorer = RiskScorer()
        stats = Stats()
        tokens = TokenTable()
        if has_mapping:
            process_record(record, mode="pseudo", detection_mode=request.detection_mode,
                          fort=request.fort, tech=request.tech,
                          tokens=tokens, stats=stats, scorer=scorer, mapping=mapping)
        scores.append(scorer.score)

    distribution = {"NUL": 0, "FAIBLE": 0, "MODÉRÉ": 0, "ÉLEVÉ": 0, "CRITIQUE": 0}
    for s in scores:
        sc = RiskScorer()
        sc.score = s
        distribution[sc.level()] += 1

    return {
        "total_enregistrements": total,
        "analyses": len(data),
        "score_moyen": sum(scores) / max(len(scores), 1),
        "distribution": distribution,
    }


@router.post("/dry-run")
async def dry_run_fichier(request: FichierAnonymiseRequest):
    """Aperçu sur N enregistrements avant traitement complet."""
    request.dry_run = True
    if request.limit is None:
        request.limit = 100
    return await anonymiser_fichier(request)


@router.post("/batch")
async def batch_dossier(
    input_dir: str,
    mapping_path: str | None = None,
    mode: str = "pseudo",
    detection_mode: str = "hybrid",
):
    """Traitement d'un dossier entier."""
    if not os.path.isdir(input_dir):
        raise HTTPException(404, f"Dossier non trouvé : {input_dir}")

    extensions = {'.json', '.csv', '.tsv', '.xlsx', '.xls', '.ods', '.docx', '.odt', '.pdf', '.txt', '.md'}
    fichiers = [
        os.path.join(input_dir, f) for f in sorted(os.listdir(input_dir))
        if os.path.splitext(f)[1].lower() in extensions
    ]

    if not fichiers:
        return {"fichiers_traites": 0, "erreur": "Aucun fichier supporté dans le dossier"}

    resultats = []
    for fichier in fichiers:
        try:
            req = FichierAnonymiseRequest(
                path=fichier, mapping_path=mapping_path,
                mode=mode, detection_mode=detection_mode,
            )
            result = await anonymiser_fichier(req)
            resultats.append({
                "fichier": os.path.basename(fichier),
                "traites": result.traites,
                "remplacements": result.remplacements,
                "duree_s": result.duree_s,
            })
        except Exception as e:
            resultats.append({"fichier": os.path.basename(fichier), "erreur": str(e)})

    return {
        "fichiers_traites": len(resultats),
        "resultats": resultats,
    }


@router.post("/analyze")
async def analyser_fichier(path: str):
    """Analyser la structure d'un fichier (types détectés, échantillon)."""
    if not os.path.exists(path):
        raise HTTPException(404, f"Fichier non trouvé : {path}")

    ext = detect_format(path)
    if ext == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
    else:
        data = load_file(path, {})

    total = len(data)
    sample = data[0] if data else {}

    # Détecter les types de champs
    champs = {}
    if isinstance(sample, dict):
        for key, value in sample.items():
            if isinstance(value, str):
                champs[key] = {"type": "string", "longueur": len(value), "exemple": value[:100]}
            elif isinstance(value, (int, float)):
                champs[key] = {"type": "number", "exemple": value}
            elif isinstance(value, bool):
                champs[key] = {"type": "boolean", "exemple": value}
            elif isinstance(value, list):
                champs[key] = {"type": "array", "longueur": len(value)}
            elif isinstance(value, dict):
                champs[key] = {"type": "object", "cles": list(value.keys())[:10]}
            else:
                champs[key] = {"type": str(type(value).__name__)}

    return {
        "fichier": os.path.basename(path),
        "format": ext,
        "total_enregistrements": total,
        "champs": champs,
    }


# =============================================================
#  Upload / Download / Progress
# =============================================================

# Répertoire des uploads temporaires
_UPLOAD_DIR = os.path.join(CONFIDENTIEL_DIR, '_uploads')
# Registre des jobs en cours (pour le SSE progress)
_jobs: dict[str, dict] = {}


@router.post("/upload")
async def upload_fichier(file: UploadFile = File(...)):
    """Upload un fichier via multipart. Retourne un ID pour le traiter ensuite."""
    os.makedirs(_UPLOAD_DIR, exist_ok=True)

    # Limiter la taille (400 Mo)
    max_size = 400 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(413, f"Fichier trop volumineux ({len(content) // (1024*1024)} Mo, max 400 Mo)")

    # Sauvegarder avec un nom unique
    file_id = str(_uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename or 'upload.bin')[1]
    upload_path = os.path.join(_UPLOAD_DIR, f"{file_id}{ext}")

    with open(upload_path, 'wb') as f:
        f.write(content)

    # Enregistrer pour le nettoyage
    _temp_files.append(upload_path)
    os.chmod(upload_path, 0o600)

    logger.info(f"Fichier uploadé : {file.filename} -> {upload_path} ({len(content)} octets)")

    return {
        "file_id": file_id,
        "filename": file.filename,
        "path": upload_path,
        "size": len(content),
        "format": ext,
    }


@router.get("/download")
async def download_fichier(path: str):
    """Télécharger un fichier résultat (anonymisé ou correspondances)."""
    if not os.path.exists(path):
        raise HTTPException(404, f"Fichier non trouvé : {path}")

    # Sécurité : whitelist des extensions autorisées
    ext = os.path.splitext(path)[1].lower()
    extensions_autorisees = {'.json', '.csv', '.xlsx', '.ods', '.docx', '.odt', '.txt', '.md', '.zip'}
    if ext not in extensions_autorisees:
        raise HTTPException(403, f"Extension non autorisée : {ext}")

    # Sécurité : le fichier doit être dans confidentiel/ ou contenir _PSEUDO
    abs_path = os.path.abspath(path)
    abs_confidentiel = os.path.abspath(CONFIDENTIEL_DIR)
    if not (abs_path.startswith(abs_confidentiel) or '_PSEUDO' in abs_path):
        raise HTTPException(403, "Seuls les fichiers générés sont téléchargeables")

    return FileResponse(
        path=abs_path,
        filename=os.path.basename(path),
        media_type='application/octet-stream',
    )


@router.get("/progress/{job_id}")
async def progress_fichier(job_id: str):
    """SSE : progression en temps réel du traitement d'un fichier."""

    async def event_generator():
        while True:
            job = _jobs.get(job_id)
            if job is None:
                yield {"event": "error", "data": json.dumps({"message": "Job non trouvé"})}
                return

            yield {
                "event": "progress",
                "data": json.dumps({
                    "job_id": job_id,
                    "total": job.get("total", 0),
                    "traites": job.get("traites", 0),
                    "pourcentage": round(job["traites"] / max(job["total"], 1) * 100, 1),
                    "statut": job.get("statut", "en_cours"),
                }),
            }

            if job.get("statut") in ("termine", "erreur"):
                return

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.post("/anonymise-async")
async def anonymiser_fichier_async(request: FichierAnonymiseRequest):
    """Lance un traitement asynchrone avec suivi de progression SSE.

    Retourne un job_id à utiliser avec GET /fichier/progress/{job_id}.
    """
    if not os.path.exists(request.path):
        raise HTTPException(404, f"Fichier non trouvé : {request.path}")

    job_id = str(_uuid.uuid4())[:8]
    _jobs[job_id] = {"total": 0, "traites": 0, "statut": "initialisation"}

    # Lancer le traitement en background
    import asyncio
    asyncio.create_task(_run_anonymisation(job_id, request))

    return {"job_id": job_id, "progress_url": f"/fichier/progress/{job_id}"}


async def _run_anonymisation(job_id: str, request: FichierAnonymiseRequest):
    """Exécute l'anonymisation en arrière-plan avec mise à jour du job."""
    try:
        mapping = request.mapping or {}
        if request.mapping_path:
            mapping = load_mapping(request.mapping_path)

        ext = detect_format(request.path)
        if ext == '.json':
            with open(request.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = [data]
        else:
            data = load_file(request.path, mapping)

        total = len(data)
        if request.limit:
            data = data[:request.limit]

        _jobs[job_id]["total"] = len(data)
        _jobs[job_id]["statut"] = "en_cours"

        tokens = TokenTable()
        stats = Stats()
        scorer = RiskScorer()
        has_mapping = bool(mapping.get('champs_sensibles') or mapping.get('texte_libre'))

        for i, record in enumerate(data):
            try:
                if has_mapping:
                    record_copy = copy.deepcopy(record)
                    process_record(
                        record_copy, mode=request.mode, detection_mode=request.detection_mode,
                        fort=request.fort, tech=request.tech,
                        tokens=tokens, stats=stats, scorer=scorer, mapping=mapping,
                    )
                    data[i] = record_copy
                else:
                    if isinstance(record, dict):
                        for key, val in record.items():
                            if not isinstance(val, str) or not val.strip():
                                continue
                            result = process_text(
                                val, mode=request.mode, detection_mode=request.detection_mode,
                                fort=request.fort, tech=request.tech,
                                tokens=tokens, stats=stats, scorer=scorer,
                            )
                            record[key] = result['texte_pseudonymise']
            except Exception as e:
                logger.error(f"Erreur enregistrement {i} : {e}")
                stats.errors += 1

            _jobs[job_id]["traites"] = i + 1

        # Sauvegarder
        output_path = save_file(data, request.path, '_PSEUDO', mapping)
        os.makedirs(CONFIDENTIEL_DIR, exist_ok=True)
        csv_path = os.path.join(CONFIDENTIEL_DIR, 'correspondances.csv')
        tokens.export_csv(csv_path)

        _jobs[job_id]["statut"] = "termine"
        _jobs[job_id]["output_path"] = output_path
        _jobs[job_id]["csv_path"] = csv_path
        _jobs[job_id]["remplacements"] = stats.total_remplacements()

        gc.collect()

    except Exception as e:
        logger.error(f"Job {job_id} échoué : {e}")
        _jobs[job_id]["statut"] = "erreur"
        _jobs[job_id]["erreur"] = str(e)
