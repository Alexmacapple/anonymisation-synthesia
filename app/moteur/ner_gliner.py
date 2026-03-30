"""
Service NER GLiNER2 — singleton avec lazy loading.
Produit des Spans compatibles avec le détecteur hybride.
"""

import logging
import re
import time

from .regex import Span

logger = logging.getLogger(__name__)

# Labels PII en français (validés en phase 0)
DEFAULT_PII_LABELS = [
    "personne", "email", "téléphone", "adresse",
    "IBAN", "numéro de sécurité sociale", "carte bancaire",
    "adresse IP", "date de naissance", "organisation",
    "lieu", "date",
]

# Mapping des labels GLiNER2 vers les types internes
TYPE_MAP_NER = {
    "personne": "personne",
    "person": "personne",
    "email": "email_txt",
    "téléphone": "tel_txt",
    "phone number": "tel_txt",
    "adresse": "adresse_txt",
    "address": "adresse_txt",
    "IBAN": "iban_txt",
    "numéro de sécurité sociale": "nir_txt",
    "carte bancaire": "cb_txt",
    "adresse IP": "ip_txt",
    "date de naissance": "date_naiss_txt",
    "organisation": "orga_txt",
    "organization": "orga_txt",
    "lieu": "ville_txt",
    "location": "ville_txt",
    "date": "date_txt",
}

# Mapping des types internes vers les catégories de risque
RISK_MAP = {
    "personne": "direct",
    "email_txt": "direct",
    "tel_txt": "direct",
    "adresse_txt": "indirect",
    "iban_txt": "finance",
    "nir_txt": "finance",
    "cb_txt": "finance",
    "ip_txt": "tech",
    "date_naiss_txt": "direct",
    "orga_txt": "indirect",
    "ville_txt": "indirect",
    "date_txt": "indirect",
}


class NERService:
    """Singleton GLiNER2 avec lazy loading et détection de device."""

    _instance = None

    def __init__(self):
        self._model = None
        self._device = None
        self._available = False
        self._load_error = None

    @classmethod
    def get_instance(cls) -> "NERService":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._check_availability()
        return cls._instance

    def _check_availability(self):
        """Vérifie si gliner2 et torch sont installés."""
        try:
            import torch
            self._device = "mps" if torch.backends.mps.is_available() else "cpu"
            from gliner2 import GLiNER2
            self._available = True
            logger.info(f"GLiNER2 disponible, device : {self._device}")
        except ImportError as e:
            self._available = False
            self._load_error = str(e)
            logger.warning(f"GLiNER2 non disponible : {e}. Mode regex uniquement.")

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def device(self) -> str | None:
        return self._device

    def _load_model(self):
        """Charge le modèle GLiNER2 (lazy loading)."""
        if self._model is not None:
            return
        if not self._available:
            raise RuntimeError(f"GLiNER2 non disponible : {self._load_error}")

        from gliner2 import GLiNER2
        logger.info("Chargement du modèle GLiNER2 fastino/gliner2-base-v1...")
        t0 = time.time()
        self._model = GLiNER2.from_pretrained("fastino/gliner2-base-v1")
        t1 = time.time()
        logger.info(f"Modèle chargé en {t1-t0:.1f}s sur {self._device}")

    def extract(self, text: str, labels: list[str] | None = None,
                threshold: float = 0.4) -> list[Span]:
        """Extrait les entités NER et retourne des Spans.

        Args:
            text: texte à analyser
            labels: labels PII (défaut : DEFAULT_PII_LABELS)
            threshold: seuil de confiance minimum

        Returns:
            Liste de Spans triés par position
        """
        if not self._available:
            return []

        self._load_model()

        if labels is None:
            labels = DEFAULT_PII_LABELS

        # Chunking pour les textes longs (> 10k chars)
        if len(text) > 10000:
            return self._extract_chunked(text, labels, threshold)

        result = self._model.extract_entities(
            text, labels,
            include_confidence=True,
            include_spans=True,
        )

        return self._result_to_spans(result, threshold)

    def _extract_chunked(self, text: str, labels: list[str],
                         threshold: float) -> list[Span]:
        """Extraction par chunks pour les textes longs."""
        chunks = self._split_text(text, max_length=10000)
        all_spans = []
        offset = 0

        for chunk in chunks:
            result = self._model.extract_entities(
                chunk, labels,
                include_confidence=True,
                include_spans=True,
            )
            spans = self._result_to_spans(result, threshold)
            # Ajuster les positions avec l'offset du chunk
            for span in spans:
                span.start += offset
                span.end += offset
                all_spans.append(span)
            offset += len(chunk)

        # Dédupliquer les entités proches (chevauchement entre chunks)
        return self._deduplicate(all_spans)

    def _result_to_spans(self, result: dict, threshold: float) -> list[Span]:
        """Convertit le résultat GLiNER2 en liste de Spans."""
        spans = []
        entities = result.get("entities", {})

        for label, items in entities.items():
            entity_type = TYPE_MAP_NER.get(label, label)
            risk_type = RISK_MAP.get(entity_type, "indirect")

            for item in items:
                if isinstance(item, dict):
                    confidence = item.get("confidence", 0)
                    if confidence < threshold:
                        continue
                    spans.append(Span(
                        start=item["start"],
                        end=item["end"],
                        entity_type=entity_type,
                        value=item["text"],
                        score=round(confidence, 4),
                        source="ner",
                        risk_type=risk_type,
                    ))

        spans.sort(key=lambda s: (s.start, -s.end))
        return spans

    @staticmethod
    def _split_text(text: str, max_length: int = 10000) -> list[str]:
        """Découpe le texte en chunks aux limites de phrases."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current = ""
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            if len(current) + len(sentence) <= max_length:
                current += sentence + " "
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence + " "
        if current:
            chunks.append(current.strip())

        return chunks

    @staticmethod
    def _deduplicate(spans: list[Span], distance: int = 50) -> list[Span]:
        """Supprime les doublons (même texte + même type + distance < seuil)."""
        seen: dict[str, list[int]] = {}
        deduped = []

        for span in spans:
            key = f"{span.entity_type}:{span.value.lower()}"
            positions = seen.get(key, [])
            is_duplicate = any(abs(span.start - pos) < distance for pos in positions)

            if not is_duplicate:
                deduped.append(span)
                if key not in seen:
                    seen[key] = []
                seen[key].append(span.start)

        return deduped

    def info(self) -> dict:
        """Retourne les informations sur le service NER."""
        return {
            "disponible": self._available,
            "device": self._device,
            "modele": "fastino/gliner2-base-v1" if self._available else None,
            "modele_charge": self._model is not None,
            "erreur": self._load_error,
        }
