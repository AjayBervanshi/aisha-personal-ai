import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List

log = logging.getLogger("AishaBrowser")

class CDPBrowserSession:
    """
    JARVIS Phase 2 (Feature 2.3): CDP Browser Automation.
    Connects to a running instance of Chrome/Chromium via Chrome DevTools Protocol (CDP)
    running on port 9222.

    Start Chrome with: google-chrome --remote-debugging-port=9222
    """
    def __init__(self, port: int = 9222):
        self.port = port
        self.base_url = f"http://localhost:{self.port}"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/json/version")
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def list_tabs(self) -> List[Dict[str, Any]]:
        """Returns a list of all open tabs/pages."""
        try:
            req = urllib.request.Request(f"{self.base_url}/json")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                # Filter out background pages/extensions
                return [t for t in data if t.get("type") == "page"]
        except Exception as e:
            log.error(f"Failed to list tabs: {e}")
            return []

    def get_active_tab_id(self) -> str:
        """Heuristic: returns the first page tab."""
        tabs = self.list_tabs()
        if tabs:
            return tabs[0].get("id", "")
        return ""

    def _send_cdp_command(self, tab_id: str, method: str, params: dict = None) -> Any:
        """
        Sends a command via the CDP WebSocket.
        Note: The full JARVIS implementation uses a persistent WebSocket connection.
        For this prototype (to avoid adding the `websockets` pip dependency to the user's laptop),
        we will rely on Chrome's HTTP endpoint /json/new to open URLs, or if we need deep execution,
        we simulate the action.
        """
        pass

    def navigate(self, url: str) -> str:
        """Opens a new tab to the specified URL using Chrome's REST API."""
        try:
            # We can create a new tab pointing to the URL
            encoded_url = urllib.parse.quote(url, safe='/:?=&')
            req = urllib.request.Request(f"{self.base_url}/json/new?{encoded_url}", method="PUT")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                title = data.get("title", url)
                return f"Successfully opened {url}"
        except Exception as e:
            return f"Failed to navigate to {url}: Make sure Chrome is running with --remote-debugging-port=9222. Error: {e}"

    def extract_text(self) -> str:
        """
        In a full WS implementation, this evaluates `document.body.innerText`.
        For the HTTP prototype, we just confirm the browser is alive.
        """
        if not self.is_available():
            return "Chrome is not running in debug mode on port 9222."
        tabs = self.list_tabs()
        if not tabs:
            return "No open tabs found."

        tab = tabs[0]
        title = tab.get("title", "Unknown Title")
        url = tab.get("url", "Unknown URL")

        return f"Currently viewing: '{title}' at {url}"

browser_controller = CDPBrowserSession()
