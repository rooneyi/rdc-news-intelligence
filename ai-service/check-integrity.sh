#!/bin/bash

# Script de vérification de l'intégrité du projet AI Service

echo "🔍 Vérification de l'intégrité du projet AI Service..."
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (MANQUANT)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (MANQUANT)"
        return 1
    fi
}

check_empty_file() {
    if [ -f "$1" ] && [ ! -s "$1" ]; then
        echo -e "${RED}✗${NC} $1 (FICHIER VIDE)"
        return 1
    fi
    return 0
}

check_no_duplicate() {
    if [ -f "main.py" ] || [ -f "app/config.py" ]; then
        echo -e "${RED}✗${NC} Fichiers redondants détectés"
        return 1
    fi
    return 0
}

echo "📁 Vérification des dossiers..."
all_ok=0
check_dir "app" || all_ok=1
check_dir "app/api/routes" || all_ok=1
check_dir "app/core" || all_ok=1
check_dir "app/db" || all_ok=1
check_dir "app/schemas" || all_ok=1
check_dir "app/services" || all_ok=1
check_dir "app/utils" || all_ok=1
echo ""

echo "📄 Vérification des fichiers essentiels..."
check_file "app/main.py" || all_ok=1
check_file "app/core/config.py" || all_ok=1
check_file "app/api/routes/articles.py" || all_ok=1
check_file "app/schemas/article.py" || all_ok=1
check_file "app/services/article_service.py" || all_ok=1
check_file "app/services/embedding_service.py" || all_ok=1
check_file "app/services/load_dataset.py" || all_ok=1
check_file ".env_file" || all_ok=1
check_file "requirements.txt" || all_ok=1
echo ""

echo "📚 Vérification de la documentation..."
check_file "ARCHITECTURE.md" || all_ok=1
check_file "GETTING_STARTED.md" || all_ok=1
check_file "REFACTORING_SUMMARY.md" || all_ok=1
check_file "DEPENDENCIES.md" || all_ok=1
check_file ".gitignore" || all_ok=1
echo ""

echo "🔎 Vérification de l'absence de fichiers problématiques..."
if [ -f "main.py" ]; then
    echo -e "${RED}✗${NC} main.py (DUPLIQUÉ - doit être supprimé)"
    all_ok=1
else
    echo -e "${GREEN}✓${NC} main.py supprimé (pas de doublon)"
fi

if [ -f "app/config.py" ]; then
    echo -e "${RED}✗${NC} app/config.py (VIDE - doit être supprimé)"
    all_ok=1
else
    echo -e "${GREEN}✓${NC} app/config.py supprimé"
fi

if [ -d "app/models" ]; then
    echo -e "${RED}✗${NC} app/models/ (DOSSIER VIDE - doit être supprimé)"
    all_ok=1
else
    echo -e "${GREEN}✓${NC} app/models/ supprimé"
fi

if [ -f "app/api/route.py" ]; then
    echo -e "${RED}✗${NC} app/api/route.py (OBSOLÈTE)"
    all_ok=1
else
    echo -e "${GREEN}✓${NC} app/api/route.py supprimé"
fi

if [ -f "app/core/logger.py" ]; then
    echo -e "${YELLOW}⚠${NC} app/core/logger.py (VIDE)"
    all_ok=1
else
    echo -e "${GREEN}✓${NC} app/core/logger.py supprimé"
fi
echo ""

echo "📊 Comptage des fichiers Python..."
PYTHON_COUNT=$(find app -name "*.py" -type f | wc -l)
echo -e "${GREEN}✓${NC} $PYTHON_COUNT fichiers Python trouvés"
echo ""

echo "⚙️  Vérification de la configuration..."
if grep -q "DB_HOST" .env_file 2>/dev/null; then
    echo -e "${GREEN}✓${NC} .env_file contient DB_HOST"
else
    echo -e "${RED}✗${NC} .env_file n'a pas DB_HOST"
    all_ok=1
fi

if grep -q "DATABASE_URL" .env_file 2>/dev/null; then
    echo -e "${GREEN}✓${NC} .env_file contient DATABASE_URL"
else
    echo -e "${RED}✗${NC} .env_file n'a pas DATABASE_URL"
    all_ok=1
fi
echo ""

echo "📋 Vérification Python (optionnelle)..."
if command -v python3 &> /dev/null; then
    # Vérifier les imports de base
    python3 -c "import sys; sys.path.insert(0, '.'); from app.main import app; print('✓ app.main importé avec succès')" 2>/dev/null && \
        echo -e "${GREEN}✓${NC} Imports FastAPI OK" || \
        echo -e "${YELLOW}⚠${NC} Importer FastAPI nécessite: pip install -r requirements.txt"
else
    echo -e "${YELLOW}⚠${NC} Python3 non trouvé (skip vérification imports)"
fi
echo ""

echo "═════════════════════════════════════════════════════════════"
if [ $all_ok -eq 0 ]; then
    echo -e "${GREEN}✅ Tout va bien! Le projet est bien structuré.${NC}"
    echo ""
    echo "Prochaines étapes:"
    echo "1. pip install -r requirements.txt"
    echo "2. Vérifier .env_file avec les bons credentials DB"
    echo "3. python -m uvicorn app.main:app --reload"
else
    echo -e "${RED}❌ Il y a des problèmes à corriger.${NC}"
    exit 1
fi
echo "═════════════════════════════════════════════════════════════"

