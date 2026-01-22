"""
Fenêtre de setup/installation pour vérifier les prérequis.
"""

import customtkinter as ctk
from typing import Callable, Optional
import threading
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.setup_checker import SetupChecker


class SetupWindow(ctk.CTkToplevel):
    """Fenêtre de vérification et installation des prérequis."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Vérification des prérequis")
        self.geometry("700x600")
        self.resizable(False, False)
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # SetupChecker
        self.checker = SetupChecker()
        
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text="Vérification des prérequis",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ctk.CTkLabel(
            main_frame,
            text="Vérification des éléments nécessaires pour l'application",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        desc_label.pack(pady=(0, 30))
        
        # Frame pour les résultats
        results_frame = ctk.CTkScrollableFrame(main_frame)
        results_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        self.check_labels = {}
        self.results_container = results_frame
        
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        # Bouton Vérifier
        self.check_button = ctk.CTkButton(
            button_frame,
            text="Vérifier",
            command=self.run_checks,
            width=150,
            height=30
        )
        self.check_button.pack(side="left", padx=10)
        
        # Bouton Installer les packages
        self.install_button = ctk.CTkButton(
            button_frame,
            text="Installer les packages",
            command=self.install_packages,
            width=200,
            height=30,
            state="disabled"
        )
        self.install_button.pack(side="left", padx=10)
        
        # Bouton Fermer
        self.close_button = ctk.CTkButton(
            button_frame,
            text="Fermer",
            command=self.destroy,
            width=150,
            height=30,
            fg_color="gray",
            hover_color="darkgray"
        )
        self.close_button.pack(side="right", padx=10)
        
        # Barre de progression (cachée initialement)
        self.progress_bar = ctk.CTkProgressBar(main_frame)
        self.progress_bar.pack(fill="x", pady=(10, 0))
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()
        
        # Message de statut
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(10, 0))
        
        # Centrer la fenêtre
        self.center_window()
        
        # Garder la fenêtre au premier plan par rapport au parent
        try:
            self.transient(parent)
        except Exception:
            pass
        self.after(100, self._bring_to_front)
        
        # Lancer la vérification automatique
        self.after(100, self.run_checks)
    
    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _bring_to_front(self):
        """Amène la fenêtre au premier plan."""
        try:
            self.update_idletasks()
            self.lift()
            self.focus_force()
            self.attributes('-topmost', True)
            self.after(150, lambda: self.attributes('-topmost', False))
        except Exception:
            pass
    
    def run_checks(self):
        """Lance la vérification des prérequis."""
        self.check_button.configure(state="disabled")
        self.status_label.configure(
            text="Vérification en cours...",
            text_color="#FFFF99"  # Jaune très clair pour les messages d'information
        )
        
        # Nettoyer les résultats précédents
        for widget in self.check_labels.values():
            widget.destroy()
        self.check_labels.clear()
        
        def check_thread():
            results = self.checker.run_all_checks()
            
            # Mettre à jour l'interface dans le thread principal
            self.after(0, lambda: self.update_check_results(results))
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def update_check_results(self, results):
        """Met à jour l'affichage des résultats."""
        all_ok = True
        packages_missing = False
        
        # Nettoyer les résultats précédents
        for widget in self.results_container.winfo_children():
            widget.destroy()
        self.check_labels.clear()
        
        for check_name, (is_ok, message) in results.items():
            if check_name == "Packages manquants":
                packages_missing = True
                continue
            
            # Créer le frame pour ce check
            frame = ctk.CTkFrame(self.results_container)
            frame.pack(fill="x", padx=5, pady=5)
            
            # Icône de statut
            status_icon = "✓" if is_ok else "✗"
            status_color = "green" if is_ok else "red"
            
            icon_label = ctk.CTkLabel(
                frame,
                text=status_icon,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=status_color,
                width=30
            )
            icon_label.pack(side="left", padx=10)
            
            # Nom du check
            name_label = ctk.CTkLabel(
                frame,
                text=check_name,
                font=ctk.CTkFont(size=14, weight="bold"),
                width=150
            )
            name_label.pack(side="left", padx=10)
            
            # Message
            msg_label = ctk.CTkLabel(
                frame,
                text=message,
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            msg_label.pack(side="left", padx=10, fill="x", expand=True)
            
            self.check_labels[check_name] = frame
            
            if not is_ok:
                all_ok = False
        
        # Vérifier s'il y a des packages manquants
        if "Packages manquants" in results:
            packages_missing = True
        
        # Mettre à jour le bouton d'installation
        if packages_missing:
            self.install_button.configure(state="normal")
        else:
            self.install_button.configure(state="disabled")
        
        # Mettre à jour le statut
        if all_ok and not packages_missing:
            self.status_label.configure(text="✓ Tous les prérequis sont satisfaits", text_color="green")
        else:
            self.status_label.configure(text="⚠ Certains prérequis manquent", text_color="orange")
        
        self.check_button.configure(state="normal")
    
    def install_packages(self):
        """Installe les packages manquants depuis requirements.txt et requirements-gui.txt."""
        self.install_button.configure(state="disabled")
        self.check_button.configure(state="disabled")
        self.progress_bar.pack(fill="x", pady=(10, 0))
        self.progress_bar.set(0.5)
        self.status_label.configure(
            text="Installation automatique des packages en cours...", 
            text_color="#FFFF99"  # Jaune très clair
        )
        
        def install_thread():
            def callback(message):
                self.after(0, lambda msg=message: self.status_label.configure(
                    text=msg,
                    text_color="#FFFF99"  # Jaune très clair pour les messages d'information
                ))
            
            # install_packages() installe automatiquement depuis requirements.txt et requirements-gui.txt
            success, message = self.checker.install_packages(callback=callback)
            
            self.after(0, lambda: self.install_finished(success, message))
        
        threading.Thread(target=install_thread, daemon=True).start()
    
    def install_finished(self, success: bool, message: str):
        """Appelé quand l'installation est terminée."""
        self.progress_bar.pack_forget()
        
        if success:
            self.status_label.configure(text="✓ Installation réussie!", text_color="green")
            # Relancer la vérification après un court délai
            self.after(1000, self.run_checks)
            # Notifier la fenêtre parente (MainWindow) pour réactiver les boutons
            # self.master est la MainWindow passée au constructeur
            parent = self.master
            if hasattr(parent, 'check_setup_status'):
                # Attendre un peu pour que les packages soient bien installés
                self.after(1500, lambda: parent.check_setup_status())
            if hasattr(parent, 'refresh_home_if_needed'):
                # Rafraîchir la page d'accueil si elle est affichée
                self.after(1600, lambda: parent.refresh_home_if_needed())
        else:
            self.status_label.configure(text=f"✗ Erreur: {message}", text_color="red")
        
        self.install_button.configure(state="normal")
        self.check_button.configure(state="normal")

