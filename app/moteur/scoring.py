"""
Scoring RGPD et statistiques de traitement.
Source : Pseudonymus pseudonymise.py lignes 351-424
"""

import sys


class RiskScorer:
    """Calcule un score de risque RGPD par enregistrement."""

    POINTS = {'finance': 5, 'direct': 3, 'tech': 2, 'indirect': 1}

    def __init__(self):
        self.score = 0
        self.details: dict[str, int] = {'direct': 0, 'finance': 0, 'tech': 0, 'indirect': 0}

    def add(self, type_name: str, count: int = 1):
        """Ajoute des détections au score."""
        points = self.POINTS.get(type_name, 1)
        self.details[type_name] = self.details.get(type_name, 0) + count
        self.score += points * count

    def level(self) -> str:
        """Retourne le niveau de risque."""
        if self.score == 0:
            return 'NUL'
        if self.score < 10:
            return 'FAIBLE'
        if self.score < 50:
            return 'MODÉRÉ'
        if self.score < 100:
            return 'ÉLEVÉ'
        return 'CRITIQUE'

    def reset(self):
        self.score = 0
        self.details = {'direct': 0, 'finance': 0, 'tech': 0, 'indirect': 0}

    def to_dict(self) -> dict:
        return {
            'total': self.score,
            'niveau': self.level(),
            'details': dict(self.details),
        }


class Stats:
    """Compteurs et échantillons de traitement."""

    def __init__(self):
        self.counts: dict[str, int] = {}
        self.samples: dict[str, list[tuple[str, str]]] = {}
        self.errors: int = 0

    def add(self, type_name: str, original: str, replacement: str):
        """Enregistre un remplacement."""
        self.counts[type_name] = self.counts.get(type_name, 0) + 1
        if type_name not in self.samples:
            self.samples[type_name] = []
        if len(self.samples[type_name]) < 5:
            self.samples[type_name].append((str(original)[:60], replacement))

    def total_remplacements(self) -> int:
        return sum(self.counts.values())

    def to_dict(self) -> dict:
        return {
            'total': self.total_remplacements(),
            'par_type': dict(self.counts),
            'erreurs': self.errors,
        }

    def report(self, total: int, processed: int, scorer: RiskScorer | None = None):
        """Affiche un rapport de traitement sur stderr."""
        print(f'\n{"=" * 60}', file=sys.stderr)
        print('RAPPORT DE TRAITEMENT', file=sys.stderr)
        print(f'{"=" * 60}', file=sys.stderr)
        print(f'Enregistrements : {processed}/{total} traités', file=sys.stderr)
        if self.errors:
            print(f'Erreurs (skippés) : {self.errors}', file=sys.stderr)
        print(f'\nRemplacements par type :', file=sys.stderr)
        for t in sorted(self.counts.keys()):
            print(f'  {t:25s} : {self.counts[t]:6d}', file=sys.stderr)
        total_repl = self.total_remplacements()
        print(f'  {"TOTAL":25s} : {total_repl:6d}', file=sys.stderr)

        if scorer:
            print(f'\nScore RGPD moyen : {scorer.score / max(processed, 1):.1f} '
                  f'({scorer.level()})', file=sys.stderr)

        print(f'\nÉchantillons (5 premiers par type) :', file=sys.stderr)
        for t in sorted(self.samples.keys()):
            print(f'  [{t}]', file=sys.stderr)
            for orig, repl in self.samples[t]:
                print(f'    {orig} -> {repl}', file=sys.stderr)
        print(f'{"=" * 60}', file=sys.stderr)
