"""Advanced logging and audit trail system."""
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: str
    event_type: str
    user: str
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: str = ""
    user_agent: str = ""
    signature: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def compute_signature(self, secret: str = "") -> str:
        """Compute cryptographic signature for integrity."""
        data = f"{self.timestamp}{self.event_type}{self.user}{self.action}{self.resource}"
        return hashlib.sha256(f"{data}{secret}".encode()).hexdigest()[:16]


class AuditLogger:
    """Provides tamper-resistant audit logging."""
    
    def __init__(self, log_dir: Path, secret: str = ""):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.log_dir / 'audit_trail.json'
        self.secret = secret
        self.entries: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load audit entries."""
        if self.audit_file.exists():
            try:
                self.entries = json.loads(self.audit_file.read_text())
            except:
                self.entries = []
    
    def _save(self):
        """Save audit entries."""
        self.audit_file.write_text(json.dumps(self.entries[-5000:], indent=2))
    
    def log(self, event_type: str, action: str, user: str = "system", 
            resource: str = "", details: Dict[str, Any] = None,
            ip_address: str = "", user_agent: str = ""):
        """Log an audit event.
        
        Args:
            event_type: Type of event (task, agent, system, security)
            action: Action performed
            user: User or agent performing action
            resource: Resource affected
            details: Additional details
            ip_address: IP address (for API requests)
            user_agent: User agent string
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            user=user,
            action=action,
            resource=resource,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        entry.signature = entry.compute_signature(self.secret)
        
        self.entries.append(entry.to_dict())
        self._save()
    
    def log_task_event(self, task_id: str, action: str, details: Dict = None):
        """Log a task-related event."""
        self.log(
            event_type="task",
            action=action,
            resource=task_id,
            details=details or {}
        )
    
    def log_agent_event(self, agent_name: str, action: str, task_id: str = "", details: Dict = None):
        """Log an agent-related event."""
        self.log(
            event_type="agent",
            action=action,
            user=agent_name,
            resource=task_id,
            details=details or {}
        )
    
    def log_security_event(self, action: str, user: str = "", details: Dict = None):
        """Log a security-related event."""
        self.log(
            event_type="security",
            action=action,
            user=user,
            details=details or {}
        )
    
    def log_system_event(self, action: str, details: Dict = None):
        """Log a system-related event."""
        self.log(
            event_type="system",
            action=action,
            details=details or {}
        )
    
    def get_entries(self, event_type: Optional[str] = None, 
                   user: Optional[str] = None,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None,
                   limit: int = 100) -> List[Dict]:
        """Query audit entries.
        
        Args:
            event_type: Filter by event type
            user: Filter by user
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            limit: Maximum entries to return
            
        Returns:
            List of matching audit entries
        """
        entries = self.entries
        
        if event_type:
            entries = [e for e in entries if e.get('event_type') == event_type]
        
        if user:
            entries = [e for e in entries if e.get('user') == user]
        
        if start_time:
            entries = [e for e in entries if e.get('timestamp') >= start_time]
        
        if end_time:
            entries = [e for e in entries if e.get('timestamp') <= end_time]
        
        return entries[-limit:][::-1]
    
    def verify_integrity(self) -> bool:
        """Verify audit trail integrity."""
        for entry in self.entries:
            temp_entry = AuditEntry(**{k: v for k, v in entry.items() if k != 'signature'})
            expected_sig = temp_entry.compute_signature(self.secret)
            
            if entry.get('signature') != expected_sig:
                return False
        
        return True
    
    def export_entries(self, start_time: Optional[str] = None, 
                      end_time: Optional[str] = None) -> str:
        """Export audit entries as JSON string."""
        entries = self.entries
        
        if start_time:
            entries = [e for e in entries if e.get('timestamp') >= start_time]
        
        if end_time:
            entries = [e for e in entries if e.get('timestamp') <= end_time]
        
        return json.dumps(entries, indent=2)
    
    def get_statistics(self, days: int = 7) -> Dict:
        """Get audit statistics."""
        from datetime import timedelta
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [e for e in self.entries if e.get('timestamp') >= cutoff]
        
        by_type = {}
        by_user = {}
        by_action = {}
        
        for entry in recent:
            event_type = entry.get('event_type', 'unknown')
            user = entry.get('user', 'unknown')
            action = entry.get('action', 'unknown')
            
            by_type[event_type] = by_type.get(event_type, 0) + 1
            by_user[user] = by_user.get(user, 0) + 1
            by_action[action] = by_action.get(action, 0) + 1
        
        return {
            'period_days': days,
            'total_events': len(recent),
            'by_type': by_type,
            'by_user': by_user,
            'by_action': by_action,
            'integrity_verified': self.verify_integrity()
        }


class StructuredLogger:
    """Provides structured logging with multiple outputs."""
    
    def __init__(self, name: str, log_dir: Path, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            file_handler = logging.FileHandler(log_dir / 'orchestrator.log')
            file_handler.setLevel(logging.DEBUG)
            
            error_handler = logging.FileHandler(log_dir / 'errors.log')
            error_handler.setLevel(logging.ERROR)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
            
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            error_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
            self.logger.addHandler(error_handler)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self.logger.info(message)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self.logger.warning(message)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self.logger.error(message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self.logger.debug(message)
    
    def task_log(self, task_id: str, agent: str, message: str):
        """Log task-specific message."""
        self.info(f"[{task_id}] [{agent}] {message}")
