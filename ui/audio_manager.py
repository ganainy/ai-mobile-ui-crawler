# ui/audio_manager.py - Handles audio alerts and media lifecycle

import logging
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

class AudioManager(QObject):
    """Handles audio alerts and media lifecycle for the UI."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_player = None
        
    def play_alert(self, kind: str = "finish") -> None:
        """
        Play an audible alert using MP3 sound files.
        
        kind:
        - 'finish' -> done-soundeffect.mp3
        - 'error'  -> error-soundeffect.mp3
        """
        try:
            from utils.paths import find_project_root
            
            # Find project root to locate sound files
            try:
                project_root = find_project_root(Path(__file__))
            except Exception:
                project_root = Path.cwd()
            
            # Determine which sound file to play
            if kind == "error":
                sound_file = project_root / "error-soundeffect.mp3"
            else:
                sound_file = project_root / "done-soundeffect.mp3"
                
            if sound_file.exists():
                # Clean up previous player
                self._cleanup_media_player()
                
                # Create a new media player instance
                self._media_player = QMediaPlayer()
                
                # Convert path to QUrl
                sound_url = QUrl.fromLocalFile(str(sound_file.absolute()))
                self._media_player.setSource(sound_url)
                
                # Handle errors
                def handle_error(error, error_string):
                    logging.debug(f"Media player error: {error_string}")
                    self._cleanup_media_player()
                    
                self._media_player.errorOccurred.connect(handle_error)
                
                # Setup cleanup timer
                QTimer.singleShot(5000, self._cleanup_media_player)
                
                # Start playback
                self._media_player.play()
                return
            else:
                logging.debug(f"Sound file not found: {sound_file}")
        except Exception as e:
            logging.debug(f"MP3 playback failed: {e}, falling back to system beep")
            
        # Fallback to system beep
        self._system_beep(kind)

    def _system_beep(self, kind: str) -> None:
        """Fallback to system beep."""
        try:
            if kind == "error":
                QApplication.beep()
                QTimer.singleShot(250, QApplication.beep)
            else:
                QApplication.beep()
        except Exception as e:
            logging.debug(f"Audio alert fallback failed: {e}")

    def _cleanup_media_player(self) -> None:
        """Clean up the media player instance."""
        if self._media_player is not None:
            try:
                self._media_player.stop()
                self._media_player.deleteLater()
            except Exception:
                pass
            self._media_player = None
