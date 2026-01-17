#!/bin/bash
# Script d'installation avec logs défilantes

set -e  # Arrêter en cas d'erreur

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour logger avec timestamp
log() {
    echo -e "[$(date +'%H:%M:%S')] $1"
}

log_info() {
    log "${BLUE}ℹ${NC} $1"
}

log_success() {
    log "${GREEN}✓${NC} $1"
}

log_warning() {
    log "${YELLOW}⚠${NC} $1"
}

log_error() {
    log "${RED}✗${NC} $1"
}

# Bannière
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Installation - Scrapers Shopify                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

log_info "Démarrage de l'installation..."

# Vérifier Python
log_info "Vérification de Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    
    log_success "Python trouvé: $PYTHON_VERSION"
    
    # Vérifier la version (Python 3.8+ requis)
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        log_error "Python 3.8+ est requis (version actuelle: $PYTHON_VERSION)"
        echo ""
        log_info "Pour installer ou mettre à jour Python:"
        echo "  • macOS: Téléchargez depuis https://www.python.org/downloads/"
        echo "  • Ou utilisez Homebrew: brew install python3"
        echo ""
        exit 1
    else
        log_success "Version de Python OK: $PYTHON_VERSION (3.8+ requis)"
    fi
else
    log_error "Python 3 n'est pas installé"
    echo ""
    log_info "Pour installer Python:"
    echo "  • macOS: Téléchargez depuis https://www.python.org/downloads/"
    echo "  • Ou utilisez Homebrew: brew install python3"
    echo ""
    exit 1
fi

# Vérifier pip
log_info "Vérification de pip..."
if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null; then
    log_success "pip disponible"
else
    log_error "pip n'est pas installé"
    exit 1
fi

# Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    log_info "Création de l'environnement virtuel..."
    python3 -m venv venv
    log_success "Environnement virtuel créé"
else
    log_info "Environnement virtuel existant trouvé"
fi

# Activer l'environnement virtuel
log_info "Activation de l'environnement virtuel..."
source venv/bin/activate

# Mettre à jour pip
log_info "Mise à jour de pip..."
python3 -m pip install --upgrade pip --quiet
log_success "pip mis à jour"

# Installer les dépendances
log_info "Installation des dépendances depuis requirements.txt..."
if [ -f "requirements.txt" ]; then
    python3 -m pip install -r requirements.txt
    log_success "Dépendances installées"
else
    log_error "Fichier requirements.txt introuvable"
    exit 1
fi

# Vérifier l'installation
log_info "Vérification de l'installation..."
python3 -c "import customtkinter; import selenium; import pandas; import bs4" 2>/dev/null
if [ $? -eq 0 ]; then
    log_success "Installation vérifiée avec succès"
else
    log_warning "Certaines dépendances pourraient être manquantes"
fi

echo ""
log_success "Installation terminée!"
echo ""
log_info "Pour lancer l'application:"
echo "  source venv/bin/activate"
echo "  python3 run_gui.py"
echo ""

