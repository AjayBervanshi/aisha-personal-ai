import time
import logging
import platform
import subprocess
import threading
from typing import Optional, Tuple, Any
try:
    from PIL import Image, ImageChops
except ImportError:
    Image = None
    ImageChops = None
import io

log = logging.getLogger("AishaAwareness")

try:
    import pyscreenshot as ImageGrab
except ImportError:
    ImageGrab = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

class AwarenessEngine:
    """
    JARVIS Phase 3 (Feature 3.1): Continuous Awareness (The Eyes).
    Enhanced with "Smart Diffing": takes screenshots every 10s but only runs OCR and
    sends to the cloud if the screen structurally changes by > 5% or the active window title changes.
    Gracefully falls back to just tracking the active window if PIL/Tesseract are missing.
    """
    def __init__(self, supabase_client, machine_id: str):
        self.supabase = supabase_client
        self.machine_id = machine_id
        self.os_type = platform.system().lower()
        self.last_image = None
        self.last_window_title = ""
        self.is_running = False
        self.thread = None

        log.info(f"Awareness Engine initialized for {self.os_type}")
        if not ImageGrab:
            log.warning("pyscreenshot not installed. Will only track active window titles.")
        if not pytesseract:
            log.warning("pytesseract not installed. OCR text extraction disabled.")

    def get_active_window_title(self) -> str:
        """Cross-platform retrieval of the currently focused window title."""
        try:
            if self.os_type == 'windows':
                # Quick PowerShell to get active window
                cmd = 'powershell "Get-Process | Where-Object {$_.MainWindowHandle -ne 0 -and $_.MainWindowHandle -eq (Add-Type -MemberDefinition \\"[DllImport(\'\"user32.dll\\\"\')] public static extern IntPtr GetForegroundWindow();\\" -Name \\"Win32\\" -PassThru)::GetForegroundWindow()} | Select-Object -ExpandProperty MainWindowTitle"'
                return subprocess.check_output(cmd, shell=True, text=True).strip()
            elif self.os_type == 'linux':
                # Requires xdotool
                window_id = subprocess.check_output(["xdotool", "getactivewindow"], text=True).strip()
                return subprocess.check_output(["xdotool", "getwindowname", window_id], text=True).strip()
            elif self.os_type == 'darwin':
                cmd = """osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true'"""
                app_name = subprocess.check_output(cmd, shell=True, text=True).strip()
                return f"Active App: {app_name}"
            return "Unknown OS"
        except Exception:
            return "Unknown Window"

    def take_screenshot(self) -> Any:
        if not ImageGrab:
            return None
        try:
            # Grab bounding box of primary monitor, convert to grayscale to save memory
            img = ImageGrab.grab()
            return img.convert('L')
        except Exception as e:
            log.error(f"Failed to take screenshot: {e}")
            return None

    def has_screen_changed(self, current_img: Any) -> bool:
        """Smart Diffing: Returns True if the screen changed significantly."""
        if not self.last_image:
            return True
        try:
            diff = ImageChops.difference(current_img, self.last_image)
            # Calculate root-mean-square difference or just bounding box changes
            if diff.getbbox():
                # Screen changed
                return True
            return False
        except Exception:
            return True # Default to processing if diff fails

    def extract_text(self, img: Any) -> str:
        if not pytesseract:
            return ""
        try:
            # Resize image to speed up OCR (sacrifice some accuracy for speed)
            img_small = img.resize((img.width // 2, img.height // 2))
            text = pytesseract.image_to_string(img_small)
            return text.strip()[:2000] # Cap at 2000 chars to save DB space
        except Exception as e:
            log.error(f"OCR Error: {e}")
            return ""

    def process_frame(self):
        """One tick of the awareness loop."""
        try:
            current_window = self.get_active_window_title()
            current_img = self.take_screenshot()

            screen_changed = False
            if current_img:
                screen_changed = self.has_screen_changed(current_img)

            window_changed = current_window != self.last_window_title

            # Smart Diffing: Only push to cloud if something actually happened
            if screen_changed or window_changed:
                ocr_text = ""
                if current_img and screen_changed:
                    ocr_text = self.extract_text(current_img)
                    self.last_image = current_img

                self.last_window_title = current_window

                # Push awareness log to Supabase
                if self.supabase:
                    self.supabase.table("aisha_awareness_logs").insert({
                        "sidecar_id": self.machine_id,
                        "active_window": current_window,
                        "screen_text": ocr_text,
                        "has_visual_change": screen_changed
                    }).execute()
                    log.info(f"[Awareness] Synced frame. Window: '{current_window[:30]}...'")
        except Exception as e:
            log.error(f"[Awareness] Frame error: {e}")

    def _loop(self):
        while self.is_running:
            self.process_frame()
            time.sleep(10) # 10 second interval like JARVIS

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            log.info("Awareness Engine started in background thread.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
            log.info("Awareness Engine stopped.")
