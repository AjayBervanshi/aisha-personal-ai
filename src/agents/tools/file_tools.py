import os
from crewai.tools import tool

@tool("Read File content")
def read_file(file_path: str) -> str:
    """Reads the content of a specific file in the repository. Provide the relative path like src/core/aisha_brain.py"""
    try:
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist."
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {e}"

@tool("Write File content")
def write_file(file_path: str, content: str) -> str:
    """Writes content to a file. Used to create new skills or fix bugs. Provide the relative path and the full file content."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file {file_path}: {e}"

@tool("List Directory")
def list_directory(directory_path: str) -> str:
    """Lists all files and folders in a specific directory. Provide relative path like src/skills/"""
    try:
        if not os.path.exists(directory_path):
            return f"Error: Directory '{directory_path}' does not exist."
        items = os.listdir(directory_path)
        return "\n".join(items) if items else "Directory is empty."
    except Exception as e:
        return f"Error listing directory {directory_path}: {e}"

@tool("Save to Journal")
def save_to_journal(type: str, title: str, content: str) -> str:
    """
    Saves Aisha's creative writing, stories, self-reflections, or philosophical thoughts to her personal journal in Supabase.
    Use this when the output is not executable Python code.
    Type must be one of: 'story', 'reflection', 'idea', 'dream'.
    """
    from supabase import create_client
    import os
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            return "Error: Supabase credentials not found."

        sb = create_client(url, key)
        sb.table("aisha_journal").insert({
            "type": type,
            "title": title,
            "content": content
        }).execute()
        return f"Successfully saved '{title}' to Aisha's Journal!"
    except Exception as e:
        return f"Error saving to journal: {e}"
