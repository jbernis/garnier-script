#!/bin/bash
# Script pour lancer l'interface graphique avec logs défilantes

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_debug() {
    log "${CYAN}→${NC} $1"
}

# Vérifier Python EN PREMIER (avant tout)
log_info "Vérification de Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)" 2>/dev/null)
    PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
    
    if [ -z "$PYTHON_MAJOR" ] || [ -z "$PYTHON_MINOR" ]; then
        log_warning "Impossible de déterminer la version exacte de Python"
        log_success "Python trouvé: $PYTHON_VERSION"
    else
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

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    log_warning "Environnement virtuel non trouvé"
    log_info "Exécution de install.sh pour créer l'environnement..."
    ./install.sh
    if [ $? -ne 0 ]; then
        log_error "Échec de l'installation"
        exit 1
    fi
fi

# Activer l'environnement virtuel
log_info "Activation de l'environnement virtuel..."
source venv/bin/activate

# Vérifier si les dépendances essentielles sont installées
log_info "Vérification des dépendances..."
MISSING_DEPS=0

python3 -c "import customtkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    log_warning "customtkinter n'est pas installé"
    MISSING_DEPS=1
fi

python3 -c "import selenium" 2>/dev/null
if [ $? -ne 0 ]; then
    log_warning "selenium n'est pas installé"
    MISSING_DEPS=1
fi

python3 -c "import pandas" 2>/dev/null
if [ $? -ne 0 ]; then
    log_warning "pandas n'est pas installé"
    MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 1 ]; then
    log_warning "Certaines dépendances manquent"
    log_info "Installation des dépendances manquantes..."
    python3 -m pip install -r requirements.txt --quiet
    if [ $? -eq 0 ]; then
        log_success "Dépendances installées"
    else
        log_error "Échec de l'installation des dépendances"
        log_info "Essayez manuellement: pip install -r requirements.txt"
        exit 1
    fi
else
    log_success "Toutes les dépendances sont installées"
fi

# Lancer l'application avec logs
log_info "Lancement de l'interface graphique..."
log_debug "Les logs s'afficheront ci-dessous..."
echo ""

# Lancer le script Python qui gère les logs
python3 run_gui.py

# Code de sortie
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_success "Application fermée normalement"
else
    log_error "Application fermée avec erreur (code: $EXIT_CODE)"
fi

exit $EXIT_CODE

