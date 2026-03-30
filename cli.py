#!/usr/bin/env python3
"""
CLI anonymisation-synthesia — pseudonymisation/anonymisation multi-format.
Combine GLiNER2 (NER contextuel) + regex/dictionnaires.

Usage :
    python cli.py fichier.json --mapping mapping.json --pseudo --mode hybrid
    python cli.py document.docx --pseudo --mode hybrid
    python cli.py fichier.json --mapping mapping.json --dry-run
    python cli.py fichier.json --mapping mapping.json --score-only
    python cli.py fichier.json --mapping-generate
    python cli.py --input-dir dossier/ --mapping mapping.json --pseudo
"""

import argparse
import copy
import json
import os
import sys
import time

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.moteur.pipeline import process_record, process_text
from app.moteur.substitution import TokenTable
from app.moteur.scoring import RiskScorer, Stats
from app.moteur.navigation import load_mapping
from app.formats.base import load_file, save_file, detect_format


def traiter_fichier(args):
    """Traite un fichier unique."""
    input_path = args.input
    mode = 'pseudo' if args.pseudo else 'anon' if args.anon else 'pseudo'
    detection_mode = args.mode
    fort = args.fort
    tech = args.tech
    dry_run = args.dry_run
    score_only = args.score_only

    # Charger le mapping si fourni
    mapping = {}
    if args.mapping:
        mapping = load_mapping(args.mapping)
        print(f'Mapping chargé : {args.mapping}', file=sys.stderr)

    # Charger le fichier
    print(f'Chargement : {input_path}...', file=sys.stderr)
    t0 = time.time()
    ext = detect_format(input_path)

    if ext == '.json':
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
    else:
        data = load_file(input_path, mapping)

    total = len(data)
    t1 = time.time()
    print(f'  {total} enregistrements chargés en {t1-t0:.1f}s', file=sys.stderr)

    # Dry-run : limiter à 100
    if dry_run:
        data = data[:100]
        print(f'  Mode dry-run : traitement de {len(data)} enregistrements', file=sys.stderr)

    # Préparer les objets partagés
    tokens = TokenTable()
    stats = Stats()
    scorer = RiskScorer()

    # Déterminer le mode de traitement
    has_mapping = bool(mapping.get('champs_sensibles') or mapping.get('texte_libre'))

    # Traitement
    options_actives = [f'mode={detection_mode}']
    if fort:
        options_actives.append('fort')
    if tech:
        options_actives.append('tech')
    print(f'\nTraitement en cours ({", ".join(options_actives)})...', file=sys.stderr)
    t0 = time.time()

    for i, record in enumerate(data):
        if has_mapping:
            record_copy = copy.deepcopy(record) if not score_only else record
            process_record(
                record_copy, mode=mode, detection_mode=detection_mode,
                fort=fort, tech=tech,
                tokens=tokens, stats=stats, scorer=scorer, mapping=mapping,
            )
            if not score_only:
                data[i] = record_copy
        else:
            # Mode sans mapping : scanner toutes les valeurs string de l'enregistrement
            if isinstance(record, dict):
                for key, val in record.items():
                    if not isinstance(val, str) or not val.strip():
                        continue
                    result = process_text(
                        val, mode=mode, detection_mode=detection_mode,
                        fort=fort, tech=tech,
                        tokens=tokens, stats=stats, scorer=scorer,
                    )
                    if not score_only:
                        record[key] = result['texte_pseudonymise']
            else:
                texte = str(record)
                if not texte:
                    continue
                result = process_text(
                    texte, mode=mode, detection_mode=detection_mode,
                    fort=fort, tech=tech,
                    tokens=tokens, stats=stats, scorer=scorer,
                )

        # Progression
        if (i + 1) % 100 == 0 or i == len(data) - 1:
            elapsed = time.time() - t0
            speed = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(data) - i - 1) / speed if speed > 0 else 0
            print(f'\r  {i+1}/{len(data)} ({speed:.0f} enreg/s, ETA {eta:.0f}s)', end='', file=sys.stderr)

    t1 = time.time()
    print(f'\n  Traitement terminé en {t1-t0:.1f}s ({detection_mode})', file=sys.stderr)

    # Rapport
    print(f'\n  Mode de détection : {detection_mode}', file=sys.stderr)
    if fort:
        print(f'  Options : fort', file=sys.stderr)
    if tech:
        print(f'  Options : tech', file=sys.stderr)
    stats.report(total, len(data), scorer)

    # Score-only : pas de sauvegarde
    if score_only:
        print(f'\nScore RGPD moyen : {scorer.score / max(len(data), 1):.1f} ({scorer.level()})', file=sys.stderr)
        return

    # Dry-run : pas de sauvegarde
    if dry_run:
        print('\nMode dry-run : aucun fichier écrit.', file=sys.stderr)
        # Afficher un aperçu
        print(json.dumps(data[:3], ensure_ascii=False, indent=2)[:2000])
        return

    # Sauvegarder le fichier anonymisé
    confidentiel_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'confidentiel')
    os.makedirs(confidentiel_dir, exist_ok=True)

    output_path = save_file(data, input_path, '_PSEUDO', mapping)
    print(f'\nFichier anonymisé : {output_path}', file=sys.stderr)

    # Sauvegarder les correspondances
    csv_path = os.path.join(confidentiel_dir, 'correspondances.csv')
    tokens.export_csv(csv_path)
    print(f'Correspondances : {csv_path} ({len(tokens.correspondances_list())} entrées)', file=sys.stderr)


def traiter_dossier(args):
    """Traite tous les fichiers d'un dossier."""
    input_dir = args.input_dir
    extensions = {'.json', '.csv', '.tsv', '.xlsx', '.xls', '.ods', '.docx', '.odt', '.pdf', '.txt', '.md'}

    fichiers = [
        os.path.join(input_dir, f) for f in sorted(os.listdir(input_dir))
        if os.path.splitext(f)[1].lower() in extensions
    ]

    if not fichiers:
        print(f'Aucun fichier supporté dans {input_dir}', file=sys.stderr)
        return

    print(f'{len(fichiers)} fichiers à traiter dans {input_dir}', file=sys.stderr)

    for fichier in fichiers:
        print(f'\n{"=" * 60}', file=sys.stderr)
        print(f'Fichier : {fichier}', file=sys.stderr)
        args.input = fichier
        try:
            traiter_fichier(args)
        except Exception as e:
            print(f'ERREUR : {e}', file=sys.stderr)
            continue


def generer_mapping(args):
    """Génère un mapping squelette depuis un fichier."""
    input_path = args.input
    ext = detect_format(input_path)

    if ext == '.json':
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            sample = data[0]
        elif isinstance(data, dict):
            sample = data
        else:
            print('Fichier vide.', file=sys.stderr)
            return
    else:
        data = load_file(input_path, {})
        if data:
            sample = data[0]
        else:
            print('Fichier vide.', file=sys.stderr)
            return

    # Analyser les clés
    mapping = {
        'description': f'Mapping auto pour {os.path.basename(input_path)}',
        'champs_sensibles': {},
        'texte_libre': [],
        'lookup_noms': {},
        'whitelist': [],
        'blacklist': [],
    }

    # Heuristiques de détection
    type_hints = {
        'nom': ['nom', 'name', 'lastname', 'surname', 'family'],
        'prenom': ['prenom', 'firstname', 'given'],
        'email': ['email', 'mail', 'courriel'],
        'tel': ['tel', 'phone', 'telephone', 'mobile'],
        'cp': ['cp', 'postal', 'zip', 'code_postal'],
        'id': ['id', 'ident', 'identifiant', 'numero'],
    }

    for key, value in sample.items() if isinstance(sample, dict) else []:
        key_lower = key.lower()
        detected = False
        for type_name, hints in type_hints.items():
            if any(h in key_lower for h in hints):
                prefix = type_name.upper()
                mapping['champs_sensibles'][key] = {'type': type_name, 'jeton': prefix}
                detected = True
                break
        if not detected and isinstance(value, str) and len(value) > 50:
            mapping['texte_libre'].append(key)

    print(json.dumps(mapping, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='Anonymisation-synthesia — pseudonymisation PII hybride (GLiNER2 + regex)',
    )
    parser.add_argument('input', nargs='?', help='Fichier à traiter')
    parser.add_argument('--mapping', help='Fichier de mapping JSON')
    parser.add_argument('--input-dir', help='Traiter un dossier entier')

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--pseudo', action='store_true', help='Pseudonymisation réversible (défaut)')
    mode_group.add_argument('--anon', action='store_true', help='Anonymisation irréversible')
    mode_group.add_argument('--dry-run', action='store_true', help='Aperçu sur 100 enregistrements')
    mode_group.add_argument('--score-only', action='store_true', help='Scoring RGPD sans anonymiser')
    mode_group.add_argument('--mapping-generate', action='store_true', help='Générer un mapping squelette')

    parser.add_argument('--mode', default='hybrid', choices=['regex', 'ner', 'hybrid'],
                        help='Mode de détection (défaut: hybrid)')
    parser.add_argument('--fort', action='store_true', help='Mode fort (prénoms isolés, propagation)')
    parser.add_argument('--tech', action='store_true', help='Détection technique (IPv4, MAC, JWT)')

    args = parser.parse_args()

    if args.mapping_generate:
        if not args.input:
            parser.error('--mapping-generate nécessite un fichier en entrée')
        generer_mapping(args)
    elif args.input_dir:
        traiter_dossier(args)
    elif args.input:
        traiter_fichier(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
