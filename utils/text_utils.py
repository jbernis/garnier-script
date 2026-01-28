"""
Utilitaires pour le traitement de texte.
"""

import unicodedata


def normalize_type(text: str) -> str:
    """
    Normalise un type de produit selon les règles :
    - MAJUSCULES
    - PLURIEL (ajout automatique si nécessaire)
    - SANS ACCENTS
    
    Args:
        text: Texte à normaliser
        
    Returns:
        Texte normalisé (ex: "Nappe" → "NAPPES", "Torchon" → "TORCHONS")
        
    Examples:
        >>> normalize_type("Nappe")
        'NAPPES'
        >>> normalize_type("Torchon")
        'TORCHONS'
        >>> normalize_type("Serviette de table")
        'SERVIETTES DE TABLE'
        >>> normalize_type("Chemin de table")
        'CHEMINS DE TABLE'
        >>> normalize_type("Plaid")
        'PLAIDS'
    """
    if not text or not text.strip():
        return ""
    
    # 1. Enlever les accents
    # Normaliser en NFD (décomposition) puis enlever les accents
    text_nfd = unicodedata.normalize('NFD', text)
    text_sans_accents = ''.join(
        char for char in text_nfd 
        if unicodedata.category(char) != 'Mn'  # Mn = Mark, Nonspacing (accents)
    )
    
    # 2. Mettre en majuscules
    text_upper = text_sans_accents.upper()
    
    # 3. Mettre au pluriel si nécessaire
    # Si le texte ne se termine pas par un 'S', ajouter un 'S'
    # Sauf pour certains cas particuliers
    
    text_upper = text_upper.strip()
    
    # Gérer les cas particuliers (ex: "Chemin de table" → "Chemins de table")
    words = text_upper.split()
    
    if len(words) > 1:
        # Plusieurs mots : pluraliser le premier mot si nécessaire
        if not words[0].endswith('S') and not words[0].endswith('X') and not words[0].endswith('Z'):
            words[0] = words[0] + 'S'
        return ' '.join(words)
    else:
        # Un seul mot : pluraliser si nécessaire
        if not text_upper.endswith('S') and not text_upper.endswith('X') and not text_upper.endswith('Z'):
            # Cas particuliers français
            if text_upper.endswith('AL'):
                # nappe → nappes (pas de règle spéciale)
                text_upper = text_upper + 'S'
            elif text_upper.endswith('AU') or text_upper.endswith('EU'):
                # Mots en -au ou -eu → ajouter X (ex: tuyau → tuyaux)
                # Mais pour les produits, on garde S (ex: plaid → plaids)
                text_upper = text_upper + 'S'
            else:
                text_upper = text_upper + 'S'
        
        return text_upper


def remove_accents(text: str) -> str:
    """
    Enlève tous les accents d'un texte.
    
    Args:
        text: Texte avec accents
        
    Returns:
        Texte sans accents
        
    Examples:
        >>> remove_accents("Élégant")
        'Elegant'
        >>> remove_accents("Café")
        'Cafe'
    """
    if not text:
        return ""
    
    # Normaliser en NFD (décomposition) puis enlever les accents
    text_nfd = unicodedata.normalize('NFD', text)
    text_sans_accents = ''.join(
        char for char in text_nfd 
        if unicodedata.category(char) != 'Mn'  # Mn = Mark, Nonspacing (accents)
    )
    
    return text_sans_accents
