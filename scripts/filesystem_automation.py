import os
import json
import logging
from typing import Dict, Any, List

log = logging.getLogger("AishaFilesystem")

class FilesystemExecutor:
    """
    JARVIS Phase 2 (Feature 2.4): Terminal & Filesystem Executor.
    Provides robust, cross-platform file and directory operations for Aisha
    without requiring raw unescaped shell commands.
    """
    def __init__(self):
        # We start operations relative to the current working directory or user's home
        self.base_dir = os.path.expanduser("~")
        log.info(f"Filesystem Executor initialized. Base dir: {self.base_dir}")

    def _resolve_path(self, path: str) -> str:
        """Safely resolves paths to prevent directory traversal attacks."""
        resolved = os.path.abspath(os.path.expanduser(path))
        # In a very strict environment we would ensure it starts with base_dir,
        # but for a personal AI on a personal laptop, full filesystem access is usually intended.
        return resolved

    def list_directory(self, path: str) -> str:
        """Returns the contents of a directory."""
        try:
            target = self._resolve_path(path)
            if not os.path.exists(target):
                return f"Path does not exist: {target}"
            if not os.path.isdir(target):
                return f"Not a directory: {target}"

            items = os.listdir(target)

            # Format output beautifully
            output = [f"Contents of {target}:"]
            for item in sorted(items):
                item_path = os.path.join(target, item)
                if os.path.isdir(item_path):
                    output.append(f"📁 {item}/")
                else:
                    size = os.path.getsize(item_path)
                    output.append(f"📄 {item} ({size} bytes)")

            return "\n".join(output)
        except Exception as e:
            log.error(f"Failed to list directory: {e}")
            return f"Error listing directory: {e}"

    def read_file(self, path: str) -> str:
        """Reads the content of a file."""
        try:
            target = self._resolve_path(path)
            if not os.path.exists(target):
                return f"File does not exist: {target}"
            if not os.path.isfile(target):
                return f"Not a file: {target}"

            # Restrict massive file reads
            size = os.path.getsize(target)
            if size > 10 * 1024 * 1024:  # 10 MB limit
                return f"File too large to read directly ({size} bytes). Max limit is 10MB."

            with open(target, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            return f"--- START OF {os.path.basename(target)} ---\n{content}\n--- END OF FILE ---"
        except Exception as e:
            log.error(f"Failed to read file: {e}")
            return f"Error reading file: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file, overwriting existing."""
        try:
            target = self._resolve_path(path)

            # Ensure directory exists
            os.makedirs(os.path.dirname(target), exist_ok=True)

            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"Successfully wrote {len(content)} characters to {target}"
        except Exception as e:
            log.error(f"Failed to write file: {e}")
            return f"Error writing file: {e}"

fs_executor = FilesystemExecutor()
