# ✅ Checklist pour les Développeurs

## 🚀 Avant de Commencer

### Installation Initiale
- [ ] Cloner le repository
- [ ] `cd ai-service`
- [ ] Créer/activer l'environnement virtuel : `source .env/bin/activate`
- [ ] Installer les dépendances : `pip install -r requirements.txt`
- [ ] Vérifier `.env` ou `.env_file` (le premier présent dans `ai-service/` est chargé — voir `app/core/config.py`)
- [ ] Vérifier PostgreSQL est en cours d'exécution
- [ ] Lancer : `python -m uvicorn app.main:app --reload`

### Vérification de Base
- [ ] API démarre sans erreur
- [ ] Accéder à http://localhost:8000/docs
- [ ] Voir la documentation Swagger des endpoints

---

## 📝 Avant de Coder

### Ajouter un Nouvel Endpoint

- [ ] Créer le fichier dans `app/services/` (par ex: `mon_service.py`)
- [ ] Créer les Pydantic models dans `app/schemas/` si nécessaire
- [ ] Ajouter les endpoints dans `app/api/routes/articles.py`
- [ ] Vérifier les imports et dépendances
- [ ] Tester avec `curl` ou Swagger UI
- [ ] Documenter avec docstrings

### Ajouter une Logique de Base de Données

- [ ] Ajouter la table SQL dans `app/db/models.py` (si nécessaire)
- [ ] Utiliser `app/db/session.py` pour les connexions
- [ ] Créer la table en direct dans PostgreSQL
- [ ] Tester la connexion

### Ajouter un Utilitaire

- [ ] Créer dans `app/utils/` (par ex: `ma_fonction.py`)
- [ ] Importer et utiliser depuis les services
- [ ] Ajouter une docstring complète
- [ ] Tester isolément si possible

---

## 🔍 Avant de Committer

### Code Quality
- [ ] Pas d'erreurs Python (vérifier avec `python -m py_compile app/**/*.py`)
- [ ] Imports organisés (stdlib, third-party, local)
- [ ] Docstrings sur les fonctions publiques
- [ ] Pas de `print()` (utiliser `logger` à la place)
- [ ] Pas de fichiers `.pyc` ou `__pycache__`

### Tests
- [ ] Tester localement avec Swagger UI
- [ ] Vérifier que l'API démarre sans warning
- [ ] Vérifier qu'aucun fichier n'a été cassé

### Git
- [ ] `git status` - Vérifier les fichiers modifiés
- [ ] Pas de fichiers inutiles (`.log`, `__pycache__`, etc.)
- [ ] Message de commit clair et descriptif
- [ ] Vérifier le `.gitignore` ignore les bons fichiers

---

## 🔧 Maintenance Régulière

### Vérification du Projet
```bash
# Lancer le script de vérification
./check-integrity.sh

# Doit afficher: ✅ Tout va bien! Le projet est bien structuré.
```

### Nettoyage des Caches
```bash
# Supprimer tous les __pycache__
find . -type d -name '__pycache__' -exec rm -rf {} +

# Supprimer les fichiers .pyc
find . -name "*.pyc" -delete
```

### Mise à Jour des Dépendances
```bash
# Afficher les dépendances outdated
pip list --outdated

# Mettre à jour pip
pip install --upgrade pip

# Mettre à jour les dépendances (avec prudence)
pip install -r requirements.txt --upgrade
```

---

## 🚨 Problèmes Courants

### Erreur: "No module named 'app'"
**Solution:**
```bash
# S'assurer qu'on est dans le bon dossier
cd ai-service

# Vérifier que l'environnement est activé
source .env/bin/activate

# Relancer
python -m uvicorn app.main:app --reload
```

### Erreur: "connection to server on socket failed"
**Solution:**
```bash
# Vérifier que PostgreSQL est lancé
sudo systemctl status postgresql
# ou (Mac)
brew services list | grep postgres

# Vérifier les credentials (.env prioritaire sur le VPS)
cat .env 2>/dev/null || cat .env_file
```

### API ne redémarre pas avec --reload
**Solution:**
```bash
# Tuer les processus Python
pkill -f "uvicorn"
pkill -f "python"

# Relancer
python -m uvicorn app.main:app --reload
```

### Erreur: "pgvector extension not found"
**Solution:**
```bash
# Connecter à PostgreSQL
psql -U postgres -h localhost -d rdc_news

# Créer l'extension
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## 📚 Documents de Référence

À consulter avant de commencer :

1. **ARCHITECTURE.md** - Comprendre la structure globale
2. **GETTING_STARTED.md** - Installation et lancement
3. **DEPENDENCIES.md** - Dépendances entre fichiers
4. **REFACTORING_SUMMARY.md** - Ce qui a changé
5. **README.md** - Vue d'ensemble du projet

---

## ✨ Best Practices

### Code Python
```python
# ✅ BON
from app.services.article_service import create_article
from app.core.config import DB_HOST

# ❌ MAUVAIS
from app.services.article_service import *
from ..core import *
```

### Logging
```python
# ✅ BON
import logging
logger = logging.getLogger(__name__)
logger.info("Quelque chose s'est passé")

# ❌ MAUVAIS
print("Debug info")
```

### Gestion d'erreurs
```python
# ✅ BON
try:
    result = dangerous_operation()
except Exception as e:
    logger.error("Erreur: %s", e)
    raise

# ❌ MAUVAIS
try:
    result = dangerous_operation()
except:
    pass
```

### Imports
```python
# ✅ BON
import os
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import DB_HOST
from app.services.article_service import create_article

# ❌ MAUVAIS
from app.services.article_service import *
import *
from . import *
```

---

## 🎯 Étapes pour Ajouter une Nouvelle Feature

1. **Planifier** - Décrire ce qui doit être fait
2. **Créer le service** - Dans `app/services/`
3. **Créer les schemas** - Dans `app/schemas/` si nécessaire
4. **Créer les routes** - Ajouter dans `app/api/routes/articles.py`
5. **Tester** - Tester localement
6. **Documenter** - Ajouter des docstrings
7. **Committer** - Avec un bon message de commit

---

## 📞 Support

Si tu as besoin d'aide :

1. Lire la documentation (ARCHITECTURE.md, DEPENDENCIES.md)
2. Lancer `./check-integrity.sh` pour vérifier l'intégrité
3. Lire les erreurs de la console attentivement
4. Vérifier que les prérequis sont installés (Python, PostgreSQL)

---

## 🎉 Prêt à Coder!

Le projet est maintenant bien structuré et documenté. Tu peux commencer à développer en toute confiance!

**Happy Coding! 🚀**

