import os
import json
import difflib
from datetime import datetime
from loguru import logger
from app.utils import utils

HISTORY_FILE_NAME = "history_scripts.json"

def get_history_file_path() -> str:
    """Returns the absolute path to history_scripts.json in the storage folder."""
    return os.path.join(utils.storage_dir(), HISTORY_FILE_NAME)

def load_history() -> list:
    """Loads script history from history_scripts.json."""
    file_path = get_history_file_path()
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception as e:
        logger.warning(f"Failed to load script history from {file_path}: {e}")
    return []

def save_script_to_history(task_id: str, subject: str, script: str, formula: str = ""):
    """Saves a successfully completed script to the history log."""
    if not script or not script.strip():
        return
    
    file_path = get_history_file_path()
    history = load_history()
    
    # Check if this task_id is already in history to avoid duplication
    if any(item.get("task_id") == task_id for item in history):
        return
        
    new_entry = {
        "task_id": task_id,
        "subject": subject,
        "formula": formula,
        "script": script.strip(),
        "created_at": datetime.now().isoformat()
    }
    history.append(new_entry)
    
    # Limit history to last 500 scripts to avoid file size bloat
    if len(history) > 500:
        history = history[-500:]
        
    try:
        # Ensure parent directories exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved script for task {task_id} to history.")
    except Exception as e:
        logger.error(f"Failed to save script to history: {e}")

def get_recent_scripts(limit: int = 5) -> list:
    """Retrieves the text of the most recent N scripts to be used for prompt exclusion."""
    history = load_history()
    # Get last N scripts, order by newest first
    recent_entries = history[-limit:] if len(history) >= limit else history
    return [entry["script"] for entry in reversed(recent_entries) if entry.get("script")]

def normalize_text(text: str) -> str:
    """Helper to strip spaces, punctuation and convert to lowercase for robust similarity check."""
    if not text:
        return ""
    # Remove common whitespace/newlines and punctuation
    text = text.lower()
    text = "".join(char for char in text if char.isalnum() or char.isspace())
    # Collapse multiple spaces into one
    return " ".join(text.split())

def is_too_similar(candidate_script: str, threshold: float = 0.8) -> tuple[bool, str, float]:
    """
    Checks if a script is too similar to any script in the history.
    Returns (is_similar, matching_script_preview, similarity_ratio).
    """
    if not candidate_script or not candidate_script.strip():
        return False, "", 0.0
        
    history = load_history()
    candidate_norm = normalize_text(candidate_script)
    
    max_ratio = 0.0
    most_similar_script = ""
    
    # We compare against the entire history (up to 500 items), which is fast enough
    for entry in history:
        prev_script = entry.get("script", "")
        if not prev_script:
            continue
            
        prev_norm = normalize_text(prev_script)
        
        # Fast heuristic: if lengths are wildly different, they are not 80% similar
        len_diff = abs(len(candidate_norm) - len(prev_norm))
        max_possible_len = max(len(candidate_norm), len(prev_norm))
        if max_possible_len > 0 and (len_diff / max_possible_len) > (1 - threshold):
            continue
            
        ratio = difflib.SequenceMatcher(None, candidate_norm, prev_norm).ratio()
        if ratio > max_ratio:
            max_ratio = ratio
            most_similar_script = prev_script
            
        if ratio >= threshold:
            return True, prev_script, ratio
            
    return False, most_similar_script, max_ratio
