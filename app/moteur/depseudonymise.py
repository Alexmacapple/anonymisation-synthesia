"""
Dépseudonymisation — restauration du texte original.
Source : Pseudonymus depseudonymise.py (67 lignes)
"""

import csv
import json
import re


def charger_correspondances(csv_path: str) -> dict[str, str]:
    """Charge un fichier CSV de correspondances (jeton → valeur originale)."""
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            jeton = row.get('jeton', '')
            valeur = row.get('valeur_originale', '')
            if jeton and valeur:
                mapping[jeton] = valeur
    return mapping


def depseudonymiser_texte(texte: str, mapping: dict[str, str]) -> tuple[str, int]:
    """Restaure un texte pseudonymisé en remplaçant les jetons.

    Les jetons sont remplacés du plus long au plus court
    pour éviter les collisions (ex: [PERSONNE_10] avant [PERSONNE_1]).

    Returns:
        Tuple (texte restauré, nombre de remplacements effectués)
    """
    resultat = texte
    count = 0
    # Trier par longueur décroissante du jeton
    for jeton, valeur in sorted(mapping.items(), key=lambda x: -len(x[0])):
        if jeton in resultat:
            resultat = resultat.replace(jeton, valeur)
            count += 1
    return resultat, count


def depseudonymiser_fichier(input_path: str, csv_path: str, output_path: str | None = None) -> str:
    """Restaure un fichier JSON pseudonymisé.

    Args:
        input_path: chemin du fichier pseudonymisé
        csv_path: chemin du CSV de correspondances
        output_path: chemin de sortie (défaut : _RESTAURE.json)

    Returns:
        Chemin du fichier restauré
    """
    mapping = charger_correspondances(csv_path)

    with open(input_path, 'r', encoding='utf-8') as f:
        contenu = f.read()

    # Remplacement global dans le contenu brut (fonctionne pour tous les formats texte)
    contenu_restaure, count = depseudonymiser_texte(contenu, mapping)

    if output_path is None:
        base, ext = input_path.rsplit('.', 1) if '.' in input_path else (input_path, 'json')
        base = re.sub(r'_PSEUDO$', '', base)
        output_path = f"{base}_RESTAURE.{ext}"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(contenu_restaure)

    return output_path
