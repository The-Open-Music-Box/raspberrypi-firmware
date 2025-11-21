# Guide de Style de Code et Pre-commit Hooks

Ce document décrit les règles de style de code et les hooks pre-commit utilisés dans le projet TheOpenMusicBox. Suivre ces règles garantit une base de code cohérente et facilite la collaboration entre développeurs.

## Table des Matières

1. [Hooks Pre-commit](#hooks-pre-commit)
2. [Règles Pydocstyle](#règles-pydocstyle)
3. [Règles Flake8](#règles-flake8)
4. [Configuration Black](#configuration-black)
5. [Configuration Isort](#configuration-isort)
6. [Docformatter](#docformatter)
7. [Bonnes Pratiques](#bonnes-pratiques)
8. [Résolution des Problèmes Courants](#résolution-des-problèmes-courants)

## Hooks Pre-commit

Le projet utilise plusieurs hooks pre-commit pour garantir la qualité du code avant chaque commit :

- **black** : Formateur de code automatique
- **isort** : Organisation des imports
- **flake8** : Linter pour détecter les erreurs et problèmes de style
- **docformatter** : Formateur de docstrings
- **pydocstyle** : Vérification des conventions de documentation

Ces hooks s'exécutent automatiquement lorsque vous tentez de faire un commit. Si l'un d'eux échoue, le commit est bloqué jusqu'à ce que les problèmes soient résolus.

## Règles Pydocstyle

Les règles pydocstyle suivantes sont activées dans notre configuration (`.pydocstyle`) :

### Règles Activées

- **D101** : Les classes publiques doivent avoir une docstring
- **D102** : Les méthodes publiques doivent avoir une docstring
- **D103** : Les fonctions publiques doivent avoir une docstring
- **D205** : Une ligne vide est requise entre la ligne de résumé et la description
- **D400** : La première ligne doit se terminer par un point

**Note** : La règle D200 (Les docstrings sur une ligne doivent tenir sur une ligne) a été désactivée pour permettre plus de flexibilité dans la présentation des docstrings courtes.

### Format Correct pour les Docstrings

```python
def ma_fonction(param1, param2):
    """Ceci est un résumé qui se termine par un point.

    Ceci est la description détaillée qui est séparée
    de la ligne de résumé par une ligne vide.

    Args:
        param1: Description du premier paramètre.
        param2: Description du deuxième paramètre.

    Returns:
        Description de ce que la fonction retourne.

    Raises:
        ExceptionType: Description des conditions qui déclenchent l'exception.
    """
    pass
```

### Erreurs Courantes et Solutions

| Erreur | Description | Solution |
|--------|-------------|----------|
| D205 | Pas de ligne vide entre le résumé et la description | Ajouter une ligne vide après la première ligne |
| D400 | La première ligne ne se termine pas par un point | Ajouter un point à la fin de la première ligne |

## Règles Flake8

Flake8 vérifie la conformité du code avec PEP 8 et détecte les erreurs potentielles.

### Règles Importantes

- **E501** : Limite de longueur de ligne (généralement 88 ou 100 caractères)
- **F401** : Imports non utilisés
- **F841** : Variables locales non utilisées
- **E302/E305** : Espacement correct entre les fonctions/classes (2 lignes vides)
- **E231** : Espacement après les virgules

### Exemple de Code Conforme

```python
import os
from typing import Dict, List, Optional

# Deux lignes vides avant les définitions de classe
class MyClass:
    """Cette classe fait quelque chose d'utile."""

    def __init__(self, param1: str, param2: int = 0):
        """Initialiser l'instance.

        Args:
            param1: Premier paramètre.
            param2: Deuxième paramètre, par défaut 0.
        """
        self.param1 = param1
        self.param2 = param2

    # Une ligne vide entre les méthodes
    def my_method(self, items: List[str]) -> Dict[str, int]:
        """Faire quelque chose avec les éléments.

        Args:
            items: Liste d'éléments à traiter.

        Returns:
            Dictionnaire des résultats.
        """
        result = {}
        for item in items:
            result[item] = len(item)
        return result
```

## Configuration Black

Black est un formateur de code qui applique un style cohérent à tout le code Python.

### Règles Principales

- Longueur de ligne maximale de 88 caractères
- Utilisation de guillemets doubles pour les chaînes
- Indentation de 4 espaces
- Espacement autour des opérateurs
- Formatage automatique des listes, dictionnaires et appels de fonction

### Comment Utiliser Black

```bash
# Formater un fichier
black app/src/services/my_file.py

# Formater tous les fichiers Python dans un répertoire
black app/src/
```

## Configuration Isort

Isort organise les imports selon un ordre standard.

### Règles d'Organisation

1. Imports standards de Python d'abord
2. Imports tiers ensuite
3. Imports locaux en dernier
4. Tri alphabétique dans chaque section

### Exemple d'Imports Bien Organisés

```python
# Imports standards
import os
import sys
from pathlib import Path

# Imports tiers
import numpy as np
import pandas as pd
from flask import Flask

# Imports locaux
from app.src.config import app_config
from app.src.helpers.exceptions import InvalidFileError
```

## Docformatter

Le tool `docformatter` est utilisé pour formater automatiquement les docstrings selon les conventions PEP 257. Il s'assure que :

- Les guillemets triples sont sur des lignes séparées
- La mise en forme est cohérente
- L'indentation est correcte
- Les listes sont correctement formatées

### Configuration de Docformatter

Pour assurer la compatibilité avec les règles pydocstyle (notamment D205 et D400), docformatter est configuré avec les arguments suivants dans notre pre-commit :

```yaml
args:
  - --in-place                # Modifie les fichiers sur place
  - --pre-summary-newline     # Assure une ligne vide après les guillemets ouvrants
  - --make-summary-multi-line # Assure que la ligne de résumé se termine par un point
  - --force-wrap              # Force le wrapping des lignes longues
  - --wrap-summaries=88       # Limite longueur des lignes de résumé
  - --wrap-descriptions=88    # Limite longueur des lignes de description
```

**Important** : Cette configuration garantit la conformité avec les règles D205 (ligne vide après le résumé) et D400 (point à la fin du résumé) exigées par notre configuration pydocstyle.

Docformatter s'assure que les docstrings suivent un format cohérent.

### Fonctionnalités Principales

- Indentation correcte des docstrings
- Espacement approprié
- Formatage des sections Args, Returns, Raises, etc.

### Comment Utiliser Docformatter

```bash
# Formater un fichier
docformatter --in-place app/src/services/my_file.py

# Formater avec options spécifiques
docformatter --in-place --make-summary-multi-line --pre-summary-newline app/src/services/my_file.py
```

## Bonnes Pratiques

### Pour les Docstrings

1. **Soyez concis mais complet** : La première ligne doit résumer clairement le but de la fonction/classe.
2. **Documentez tous les paramètres** : Chaque paramètre doit être documenté avec son type et sa fonction.
3. **Documentez les valeurs de retour** : Précisez ce que la fonction retourne.
4. **Documentez les exceptions** : Indiquez quelles exceptions peuvent être levées et dans quelles conditions.

### Pour le Style de Code

1. **Exécutez les outils de formatage avant de commit** : Utilisez `black` et `isort` pour formater votre code.
2. **Limitez la longueur des lignes** : Gardez les lignes sous 88 caractères.
3. **Utilisez des noms descriptifs** : Les noms de variables et de fonctions doivent être clairs et descriptifs.
4. **Suivez les conventions de nommage** :
   - `snake_case` pour les variables et fonctions
   - `PascalCase` pour les classes
   - `UPPER_SNAKE_CASE` pour les constantes

## Résolution des Problèmes Courants

### Contourner Temporairement les Hooks

Dans certains cas, vous pourriez avoir besoin de contourner temporairement les hooks pre-commit :

```bash
git commit --no-verify -m "Message de commit"
```

**Note** : Cette pratique doit être utilisée avec parcimonie et uniquement dans des situations exceptionnelles.

### Résoudre les Erreurs Pydocstyle

1. **D205 (ligne vide manquante)** :
   ```python
   def ma_fonction():
       """Ceci est un résumé.

       Ceci est la description.
       """
   ```

2. **D400 (point manquant)** :
   ```python
   def ma_fonction():
       """Ceci est un résumé qui se termine par un point.
       """
   ```

### Résoudre les Erreurs Flake8

1. **E501 (ligne trop longue)** :
   - Divisez les longues chaînes de caractères
   - Utilisez des parenthèses pour diviser les expressions
   - Réorganisez la logique en plusieurs lignes

2. **F401 (import non utilisé)** :
   - Supprimez les imports non utilisés
   - Si l'import est nécessaire pour les effets secondaires, ajoutez `# noqa: F401`

---

Ce guide est un document vivant qui sera mis à jour au fur et à mesure que les standards de code évoluent. Pour toute question ou suggestion, veuillez contacter l'équipe de développement.
