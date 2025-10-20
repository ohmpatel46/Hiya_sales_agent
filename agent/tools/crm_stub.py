from typing import Dict, Any
from datetime import datetime
import json
import os


def log_outcome(lead: Dict[str, Any], outcome: str, meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Log interaction outcome to CRM stub
    
    Args:
        lead: Lead information
        outcome: Outcome type (e.g., "interested", "rejected", "requested_info")
        meta: Additional metadata
    
    Returns:
        Dict with logging result
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": "outcome",
        "lead": lead,
        "outcome": outcome,
        "meta": meta or {}
    }
    
    return _append_to_log(log_entry)


def log_followup(lead: Dict[str, Any], when: str, meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Log follow-up request to CRM stub
    
    Args:
        lead: Lead information
        when: When to follow up (ISO datetime string)
        meta: Additional metadata
    
    Returns:
        Dict with logging result
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": "followup",
        "lead": lead,
        "when": when,
        "meta": meta or {}
    }
    
    return _append_to_log(log_entry)


def _append_to_log(log_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Append entry to CRM log file"""
    log_file = "./crm_log.jsonl"
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Append to log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return {
            "logged": True,
            "file": log_file,
            "entry": log_entry
        }
        
    except Exception as e:
        return {
            "logged": False,
            "error": str(e),
            "entry": log_entry
        }
