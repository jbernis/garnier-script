"""
Fenêtre de progression pour afficher l'avancement du scraping.
"""

import customtkinter as ctk
from typing import Optional, Callable
import threading
import os
import platform
import shutil
from tkinter import filedialog


class ProgressWindow(ctk.CTkToplevel):
    """Fenêtre affichant la progression du scraping."""
    
    def __init__(self, parent, title: str = "Progression"):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("800x600")
        self.resizable(True, True)
        
        # Variables
        self.is_cancelled = False
        self.output_file: Optional[str] = None
        
        # Configuration CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Titre
        title_label = ctk.CTkLabel(
            main_frame,
            text=title,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Barre de progression
        self.progress_label = ctk.CTkLabel(
            main_frame,
            text="Initialisation...",
            font=ctk.CTkFont(size=14)
        )
        self.progress_label.pack(pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(main_frame)
        self.progress_bar.pack(fill="x", pady=(0, 20))
        self.progress_bar.set(0)
        
        # Zone de notification pour les erreurs (cachée par défaut)
        self.notification_frame = ctk.CTkFrame(main_frame, fg_color=("orange", "darkorange"))
        self.notification_label = ctk.CTkLabel(
            self.notification_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("black", "white"),
            wraplength=700,
            justify="left"
        )
        self.notification_label.pack(padx=15, pady=10, fill="x")
        # Cachée par défaut
        self.notification_frame.pack_forget()
        
        # Zone de logs
        self.log_label = ctk.CTkLabel(
            main_frame,
            text="Logs:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.log_label.pack(anchor="w", pady=(0, 10))
        
        # Textbox pour les logs avec scrollbar
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        self.log_textbox = ctk.CTkTextbox(log_frame, height=300, state="normal")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        # Configurer le textbox pour être éditable et afficher les logs
        self.log_textbox.configure(state="normal")
        
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(0, 10))
        
        # Bouton Fermer
        self.close_button = ctk.CTkButton(
            button_frame,
            text="Fermer",
            command=self.close_window,
            fg_color="gray",
            hover_color="darkgray"
        )
        self.close_button.pack(side="left", padx=10)
        
        # Bouton Télécharger le fichier (caché initialement)
        self.download_button = ctk.CTkButton(
            button_frame,
            text="Télécharger le fichier",
            command=self.download_file,
            state="disabled",
            fg_color="green",
            hover_color="darkgreen"
        )
        self.download_button.pack(side="right", padx=10)
        
        # Centrer la fenêtre
        self.center_window()

        # Garder la fenêtre au premier plan par rapport au parent
        try:
            self.transient(parent)
        except Exception:
            pass
        self.after(100, self._bring_to_front)
    
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
    
    def update_progress(self, message: str, current: int = 0, total: int = 0):
        """Met à jour la barre de progression (thread-safe)."""
        # Planifier l'exécution dans le thread GUI principal
        self.after(0, self._update_progress_safe, message, current, total)
    
    def _update_progress_safe(self, message: str, current: int, total: int):
        """Met à jour la barre de progression (appelé depuis le thread GUI)."""
        try:
            if self.is_cancelled:
                return
            
            if not self.winfo_exists():
                return
        except Exception:
            return
        
        # Chaque modification est protégée individuellement
        try:
            if hasattr(self, 'progress_label'):
                self.progress_label.configure(text=message)
        except Exception:
            pass
        
        try:
            if hasattr(self, 'progress_bar'):
                if total > 0:
                    progress = current / total
                    self.progress_bar.set(progress)
                else:
                    self.progress_bar.set(0.5)
        except Exception:
            pass
        
        try:
            self.update_idletasks()
        except Exception:
            pass
    
    def show_diagnostic_notification(self, error_count: int):
        """Affiche une notification recommandant le diagnostic si des erreurs sont présentes."""
        if error_count > 0:
            try:
                if hasattr(self, 'notification_frame') and hasattr(self, 'notification_label') and hasattr(self, 'log_label'):
                    self.notification_label.configure(
                        text=f"⚠️ Attention : {error_count} produit(s) en erreur détecté(s) dans la base de données.\n"
                             f"💡 Il est recommandé de faire un diagnostic au préalable pour identifier et corriger les erreurs."
                    )
                    # Afficher la notification avant la zone de logs
                    if not self.notification_frame.winfo_viewable():
                        self.notification_frame.pack(fill="x", padx=10, pady=(0, 10), before=self.log_label)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Erreur lors de l'affichage de la notification: {e}")
    
    def add_log(self, message: str):
        """Ajoute un message aux logs (thread-safe)."""
        # Planifier l'exécution dans le thread GUI principal
        try:
            self.after(0, self._add_log_safe, message)
        except Exception:
            # Si after() échoue (fenêtre détruite), afficher dans la console
            print(f"[LOG] {message}")
    
    def _add_log_safe(self, message: str):
        """Ajoute réellement le message aux logs (appelé depuis le thread GUI)."""
        try:
            # Vérifier que la fenêtre et le widget existent encore
            if not self.winfo_exists():
                return
        except Exception:
            return
        
        try:
            if not hasattr(self, 'log_textbox'):
                return
            
            # Toutes les modifications protégées ensemble
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{message}\n", "yellow_text")
            self.log_textbox.see("end")
            self.update_idletasks()
        except Exception as e:
            # En cas d'erreur, afficher dans la console seulement si ce n'est pas une erreur de widget détruit
            if "invalid command name" not in str(e).lower() and "application has been destroyed" not in str(e).lower():
                print(f"[LOG] {message}")
    
    def close_window(self):
        """Ferme simplement la fenêtre sans affecter le script."""
        try:
            if self.winfo_exists():
                self.destroy()
        except:
            pass
    
    def cancel(self):
        """Annule le scraping (thread-safe)."""
        self.is_cancelled = True
        # Planifier l'exécution dans le thread GUI principal
        try:
            self.after(0, self._cancel_safe)
        except Exception:
            pass
    
    def _cancel_safe(self):
        """Annulation interne (appelé depuis le thread GUI)."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        
        try:
            if hasattr(self, 'close_button'):
                self.close_button.configure(state="disabled", text="Annulation...")
        except Exception:
            pass
        
        try:
            self._add_log_safe("Annulation demandée... Arrêt du script en cours...")
        except Exception:
            pass
        
        try:
            self.update_idletasks()
        except Exception:
            pass
    
    def enable_manual_close(self):
        """Ne fait rien - la fenêtre se ferme automatiquement après annulation."""
        pass
    
    def finish(self, success: bool, output_file: Optional[str] = None, error: Optional[str] = None):
        """Termine l'affichage de la progression (thread-safe)."""
        # Planifier l'exécution dans le thread GUI principal
        try:
            self.after(0, self._finish_safe, success, output_file, error)
        except Exception:
            # Si after() échoue (fenêtre détruite), ne rien faire
            pass
    
    def _finish_safe(self, success: bool, output_file: Optional[str] = None, error: Optional[str] = None):
        """Termine l'affichage de la progression (appelé depuis le thread GUI)."""
        # Vérifier que la fenêtre n'a pas été détruite
        try:
            if not self.winfo_exists():
                return
        except:
            return
        
        # Ne pas forcer is_cancelled à True ici - il doit rester à sa valeur actuelle
        # (True seulement si l'utilisateur a réellement annulé via cancel())
        
        try:
            # Stocker le fichier de sortie même si success est False (au cas où un fichier partiel aurait été créé)
            self.output_file = output_file
            
            # Vérifier si le fichier existe réellement sur le disque
            file_exists = False
            if output_file:
                file_exists = os.path.exists(output_file)
                if not file_exists:
                    # Essayer avec un chemin absolu si c'est un chemin relatif
                    abs_path = os.path.abspath(output_file)
                    if os.path.exists(abs_path):
                        file_exists = True
                        self.output_file = abs_path
                        output_file = abs_path
            
            # Logs de débogage pour comprendre le problème
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"finish() - success={success}, output_file={output_file}, file_exists={file_exists}, is_cancelled={self.is_cancelled}, error={error}")
            
            if success and not self.is_cancelled:
                try:
                    if hasattr(self, 'progress_bar'):
                        self.progress_bar.set(1.0)
                except Exception:
                    pass
                try:
                    if hasattr(self, 'progress_label'):
                        self.progress_label.configure(text="Terminé avec succès!")
                except Exception:
                    pass
                
                if output_file and file_exists:
                    self.add_log(f"\n✓ Fichier généré: {output_file}")
                    try:
                        if hasattr(self, 'download_button'):
                            self.download_button.configure(state="normal")
                            self.update()
                            logger.info("Bouton télécharger activé (success=True)")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'activation du bouton: {e}")
                elif output_file:
                    self.add_log(f"\n⚠ Fichier attendu mais introuvable: {output_file}")
                    logger.warning(f"Fichier introuvable: {output_file}")
            else:
                # Si annulé, ne pas afficher de fichier même si output_file existe
                if self.is_cancelled or (error and "Annulation" in error):
                    try:
                        if hasattr(self, 'progress_label'):
                            self.progress_label.configure(text="Annulé")
                    except Exception:
                        pass
                    self.output_file = None  # S'assurer qu'aucun fichier n'est disponible
                    try:
                        if hasattr(self, 'download_button'):
                            self.download_button.configure(state="disabled")
                    except Exception:
                        pass
                else:
                    try:
                        if hasattr(self, 'progress_label'):
                            self.progress_label.configure(text="Erreur")
                    except Exception:
                        pass
                    
                    # Même en cas d'erreur, activer le bouton si un fichier existe
                    if file_exists:
                        self.add_log(f"\n✓ Fichier généré (malgré erreur): {output_file}")
                        try:
                            if hasattr(self, 'download_button'):
                                self.download_button.configure(state="normal")
                                self.update()
                                logger.info("Bouton télécharger activé (success=False mais fichier existe)")
                        except Exception as e:
                            logger.error(f"Erreur lors de l'activation du bouton: {e}")
                
                if error:
                    self.add_log(f"\n✗ {error}")
            
            # Vérification finale : activer le bouton si le fichier existe, indépendamment de success
            # (au cas où success serait False mais qu'un fichier aurait quand même été créé)
            if file_exists:
                try:
                    if hasattr(self, 'download_button'):
                        is_cancelled_state = self.is_cancelled or (error and "Annulation" in str(error))
                        if not is_cancelled_state:
                            try:
                                current_state = self.download_button.cget("state")
                            except Exception:
                                current_state = "unknown"
                            
                            if current_state == "disabled" or current_state == "unknown":
                                try:
                                    self.download_button.configure(state="normal")
                                    self.update()
                                    logger.info(f"Bouton télécharger activé (vérification finale): {output_file}")
                                    if not (success and not self.is_cancelled):
                                        self.add_log(f"\n✓ Fichier disponible: {output_file}")
                                except Exception:
                                    pass
                            elif current_state == "normal":
                                logger.info(f"Bouton télécharger déjà activé: {output_file}")
                            else:
                                logger.warning(f"Bouton télécharger non activé - state={current_state}, is_cancelled={is_cancelled_state}, file_exists={file_exists}, output_file={output_file}")
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification finale du bouton: {e}")
            
            # Si annulé, fermer automatiquement après un court délai
            if not success and error and ("Annulation" in error or self.is_cancelled):
                def close_window():
                    try:
                        if self.winfo_exists():
                            self.destroy()
                    except:
                        pass
                self.after(500, close_window)  # Fermer après 0.5 seconde
        except Exception as e:
            import logging
            logging.error(f"Erreur dans finish(): {e}", exc_info=True)
    
    def download_file(self):
        """Télécharge le fichier CSV généré."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=" * 60)
        logger.info("download_file() APPELÉE")
        logger.info("=" * 60)
        
        if not self.output_file or not os.path.exists(self.output_file):
            logger.warning(f"download_file() - Fichier introuvable: {self.output_file}")
            self.add_log("✗ Fichier introuvable")
            return
        
        try:
            from datetime import datetime
            import re
            
            # Obtenir le nom du fichier source
            source_file = os.path.abspath(self.output_file)
            original_filename = os.path.basename(source_file)
            
            logger.info(f"download_file() - Fichier source: {source_file}")
            logger.info(f"download_file() - Nom original: {original_filename}")
            
            # Extraire le nom de base (sans extension)
            base_name, ext = os.path.splitext(original_filename)
            
            # Remplacer la date/heure existante par la date/heure actuelle
            # Format attendu: YYYYMMDD_HHMMSS (ex: 20260105_183045)
            timestamp_pattern = r'_\d{8}_\d{6}(?=\.csv|$)'
            new_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            logger.info(f"download_file() - Pattern: {timestamp_pattern}")
            logger.info(f"download_file() - Nouveau timestamp: {new_timestamp}")
            
            match = re.search(timestamp_pattern, base_name)
            if match:
                logger.info(f"download_file() - Match trouvé: {match.group()}")
                # Remplacer l'ancien timestamp par le nouveau
                new_filename = re.sub(timestamp_pattern, f'_{new_timestamp}', base_name) + ext
                logger.info(f"download_file() - Nouveau nom généré: {new_filename}")
            else:
                logger.warning(f"download_file() - Aucun timestamp trouvé dans: {base_name}")
                # Si pas de timestamp trouvé, ajouter le nouveau à la fin
                new_filename = f"{base_name}_{new_timestamp}{ext}"
                logger.info(f"download_file() - Nouveau nom (ajout): {new_filename}")
            
            # Demander à l'utilisateur où sauvegarder le fichier
            destination = filedialog.asksaveasfilename(
                title="Enregistrer le fichier CSV",
                defaultextension=".csv",
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
                initialfile=new_filename
            )
            
            logger.info(f"download_file() - Destination choisie: {destination}")
            
            if destination:
                # Copier le fichier vers l'emplacement choisi
                shutil.copy2(source_file, destination)
                self.add_log(f"✓ Fichier téléchargé: {destination}")
                
                # Ouvrir le dossier de destination
                folder_path = os.path.dirname(destination)
                system = platform.system()
                try:
                    if system == "Darwin":  # macOS
                        os.system(f'open "{folder_path}"')
                    elif system == "Windows":
                        os.system(f'explorer "{folder_path}"')
                    else:  # Linux
                        os.system(f'xdg-open "{folder_path}"')
                except Exception as e:
                    self.add_log(f"Note: Impossible d'ouvrir le dossier: {e}")
            else:
                self.add_log("Téléchargement annulé")
        except Exception as e:
            self.add_log(f"✗ Erreur lors du téléchargement: {e}")

