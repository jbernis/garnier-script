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
        
        # Zone de logs
        log_label = ctk.CTkLabel(
            main_frame,
            text="Logs:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        log_label.pack(anchor="w", pady=(0, 10))
        
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
        """Met à jour la barre de progression."""
        if self.is_cancelled:
            return
        
        self.progress_label.configure(text=message)
        
        if total > 0:
            progress = current / total
            self.progress_bar.set(progress)
        else:
            # Mode indéterminé
            self.progress_bar.set(0.5)
        
        self.update()
    
    def add_log(self, message: str):
        """Ajoute un message aux logs."""
        # Vérifier que la fenêtre et le widget existent encore
        try:
            if not self.winfo_exists():
                return
        except:
            return
        
        # Permettre l'affichage des logs même après annulation (pour les messages d'annulation)
        try:
            # Vérifier que le widget existe encore
            if not hasattr(self, 'log_textbox') or not self.log_textbox.winfo_exists():
                return
            
            # S'assurer que le textbox est en mode normal pour pouvoir écrire
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{message}\n", "yellow_text")
            self.log_textbox.see("end")
            # Garder en mode normal pour permettre l'édition continue
            self.update_idletasks()
        except Exception as e:
            # En cas d'erreur, essayer d'afficher dans la console seulement si ce n'est pas une erreur de widget détruit
            if "invalid command name" not in str(e).lower():
                print(f"Erreur lors de l'ajout du log: {e}")
                print(f"Message: {message}")
    
    def close_window(self):
        """Ferme simplement la fenêtre sans affecter le script."""
        try:
            if self.winfo_exists():
                self.destroy()
        except:
            pass
    
    def cancel(self):
        """Annule le scraping."""
        self.is_cancelled = True
        if hasattr(self, 'close_button') and self.close_button.winfo_exists():
            self.close_button.configure(state="disabled", text="Annulation...")
        self.add_log("Annulation demandée... Arrêt du script en cours...")
        # Forcer la mise à jour immédiate
        self.update_idletasks()
    
    def enable_manual_close(self):
        """Ne fait rien - la fenêtre se ferme automatiquement après annulation."""
        pass
    
    def finish(self, success: bool, output_file: Optional[str] = None, error: Optional[str] = None):
        """Termine l'affichage de la progression."""
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
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                    self.progress_bar.set(1.0)
                if hasattr(self, 'progress_label') and self.progress_label.winfo_exists():
                    self.progress_label.configure(text="Terminé avec succès!")
                
                if output_file and file_exists:
                    self.add_log(f"\n✓ Fichier généré: {output_file}")
                    try:
                        if hasattr(self, 'download_button'):
                            try:
                                if self.download_button.winfo_exists():
                                    self.download_button.configure(state="normal")
                                    self.update()  # Forcer la mise à jour de l'interface
                                    logger.info("Bouton télécharger activé (success=True)")
                            except Exception:
                                # Si winfo_exists() échoue, essayer quand même de configurer
                                self.download_button.configure(state="normal")
                                self.update()
                                logger.info("Bouton télécharger activé (success=True, sans winfo_exists)")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'activation du bouton: {e}")
                elif output_file:
                    self.add_log(f"\n⚠ Fichier attendu mais introuvable: {output_file}")
                    logger.warning(f"Fichier introuvable: {output_file}")
            else:
                # Si annulé, ne pas afficher de fichier même si output_file existe
                if self.is_cancelled or (error and "Annulation" in error):
                    if hasattr(self, 'progress_label') and self.progress_label.winfo_exists():
                        self.progress_label.configure(text="Annulé")
                    self.output_file = None  # S'assurer qu'aucun fichier n'est disponible
                    if hasattr(self, 'download_button') and self.download_button.winfo_exists():
                        self.download_button.configure(state="disabled")
                else:
                    if hasattr(self, 'progress_label') and self.progress_label.winfo_exists():
                        self.progress_label.configure(text="Erreur")
                    
                    # Même en cas d'erreur, activer le bouton si un fichier existe
                    if file_exists:
                        self.add_log(f"\n✓ Fichier généré (malgré erreur): {output_file}")
                        try:
                            if hasattr(self, 'download_button'):
                                try:
                                    if self.download_button.winfo_exists():
                                        self.download_button.configure(state="normal")
                                        self.update()
                                        logger.info("Bouton télécharger activé (success=False mais fichier existe)")
                                except Exception:
                                    self.download_button.configure(state="normal")
                                    self.update()
                                    logger.info("Bouton télécharger activé (success=False, sans winfo_exists)")
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
                                    if self.download_button.winfo_exists():
                                        self.download_button.configure(state="normal")
                                        self.update()
                                        logger.info(f"Bouton télécharger activé (vérification finale): {output_file}")
                                        if not (success and not self.is_cancelled):
                                            self.add_log(f"\n✓ Fichier disponible: {output_file}")
                                except Exception:
                                    # Si winfo_exists() échoue, essayer quand même
                                    self.download_button.configure(state="normal")
                                    self.update()
                                    logger.info(f"Bouton télécharger activé (vérification finale, sans winfo_exists): {output_file}")
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
        if not self.output_file or not os.path.exists(self.output_file):
            self.add_log("✗ Fichier introuvable")
            return
        
        try:
            # Obtenir le nom du fichier source
            source_file = os.path.abspath(self.output_file)
            filename = os.path.basename(source_file)
            
            # Demander à l'utilisateur où sauvegarder le fichier
            destination = filedialog.asksaveasfilename(
                title="Enregistrer le fichier CSV",
                defaultextension=".csv",
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
                initialfile=filename
            )
            
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

