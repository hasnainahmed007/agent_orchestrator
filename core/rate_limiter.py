"""Rate limiting and API quota management."""
import time
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    max_tokens_per_request: int = 4000
    cooldown_after_error: int = 5


@dataclass
class RateLimitStatus:
    """Current rate limit status."""
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    requests_this_day: int = 0
    is_limited: bool = False
    retry_after: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


class RateLimiter:
    """Manages API rate limits and quotas."""
    
    def __init__(self, state_dir: Path, config: Optional[RateLimitConfig] = None):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or RateLimitConfig()
        self.state_file = self.state_dir / 'rate_limits.json'
        self.request_log: List[float] = []
        self.error_timestamps: List[float] = []
        self._load()
    
    def _load(self):
        """Load rate limit state."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.request_log = data.get('request_log', [])
                self.error_timestamps = data.get('error_timestamps', [])
            except:
                self.request_log = []
                self.error_timestamps = []
    
    def _save(self):
        """Save rate limit state."""
        cutoff = time.time() - 86400
        self.request_log = [t for t in self.request_log if t > cutoff]
        self.error_timestamps = [t for t in self.error_timestamps if t > cutoff - 300]
        
        data = {
            'request_log': self.request_log,
            'error_timestamps': self.error_timestamps
        }
        self.state_file.write_text(json.dumps(data))
    
    def check_rate_limit(self) -> RateLimitStatus:
        """Check if request is within rate limits.
        
        Returns:
            RateLimitStatus with current limits and whether request is allowed
        """
        now = time.time()
        
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400
        
        requests_this_minute = sum(1 for t in self.request_log if t > minute_ago)
        requests_this_hour = sum(1 for t in self.request_log if t > hour_ago)
        requests_this_day = sum(1 for t in self.request_log if t > day_ago)
        
        status = RateLimitStatus(
            requests_this_minute=requests_this_minute,
            requests_this_hour=requests_this_hour,
            requests_this_day=requests_this_day
        )
        
        if requests_this_minute >= self.config.requests_per_minute:
            status.is_limited = True
            status.retry_after = 60.0
            return status
        
        if requests_this_hour >= self.config.requests_per_hour:
            status.is_limited = True
            status.retry_after = 3600.0
            return status
        
        if requests_this_day >= self.config.requests_per_day:
            status.is_limited = True
            status.retry_after = 86400.0
            return status
        
        if self._is_in_cooldown():
            status.is_limited = True
            status.retry_after = self._get_cooldown_remaining()
            return status
        
        return status
    
    def _is_in_cooldown(self) -> bool:
        """Check if we're in cooldown after errors."""
        if not self.error_timestamps:
            return False
        
        now = time.time()
        recent_errors = [t for t in self.error_timestamps if t > now - 60]
        
        if len(recent_errors) >= 3:
            return now - recent_errors[-1] < self.config.cooldown_after_error
        
        return False
    
    def _get_cooldown_remaining(self) -> float:
        """Get remaining cooldown time."""
        if not self.error_timestamps:
            return 0.0
        
        now = time.time()
        recent_errors = [t for t in self.error_timestamps if t > now - 60]
        
        if recent_errors:
            elapsed = now - recent_errors[-1]
            return max(0, self.config.cooldown_after_error - elapsed)
        
        return 0.0
    
    def record_request(self):
        """Record a successful request."""
        now = time.time()
        self.request_log.append(now)
        self._save()
    
    def record_error(self):
        """Record an API error."""
        now = time.time()
        self.error_timestamps.append(now)
        self._save()
    
    def wait_if_needed(self) -> float:
        """Wait if rate limited, return wait time.
        
        Returns:
            Seconds waited (0 if no wait needed)
        """
        status = self.check_rate_limit()
        
        if status.is_limited and status.retry_after > 0:
            wait_time = min(status.retry_after, 300)
            time.sleep(wait_time)
            return wait_time
        
        return 0.0
    
    def get_status(self) -> Dict:
        """Get current rate limit status."""
        status = self.check_rate_limit()
        
        return {
            'status': status.to_dict(),
            'limits': {
                'requests_per_minute': self.config.requests_per_minute,
                'requests_per_hour': self.config.requests_per_hour,
                'requests_per_day': self.config.requests_per_day,
                'max_tokens_per_request': self.config.max_tokens_per_request
            },
            'usage_percentage': {
                'per_minute': round((status.requests_this_minute / self.config.requests_per_minute) * 100, 1),
                'per_hour': round((status.requests_this_hour / self.config.requests_per_hour) * 100, 1),
                'per_day': round((status.requests_this_day / self.config.requests_per_day) * 100, 1)
            }
        }
    
    def reset(self):
        """Reset all rate limit counters."""
        self.request_log = []
        self.error_timestamps = []
        self._save()


class TokenQuotaManager:
    """Manages token quotas per request and per task."""
    
    def __init__(self, max_tokens_per_request: int = 4000, max_tokens_per_task: int = 50000):
        self.max_tokens_per_request = max_tokens_per_request
        self.max_tokens_per_task = max_tokens_per_task
        self.task_token_usage: Dict[str, int] = {}
    
    def check_task_quota(self, task_id: str) -> bool:
        """Check if task is within token quota."""
        used = self.task_token_usage.get(task_id, 0)
        return used < self.max_tokens_per_task
    
    def get_remaining_task_tokens(self, task_id: str) -> int:
        """Get remaining tokens for a task."""
        used = self.task_token_usage.get(task_id, 0)
        return max(0, self.max_tokens_per_task - used)
    
    def record_token_usage(self, task_id: str, tokens: int):
        """Record token usage for a task."""
        current = self.task_token_usage.get(task_id, 0)
        self.task_token_usage[task_id] = current + tokens
    
    def get_task_usage(self, task_id: str) -> Dict:
        """Get token usage for a task."""
        used = self.task_token_usage.get(task_id, 0)
        return {
            'task_id': task_id,
            'tokens_used': used,
            'tokens_remaining': self.get_remaining_task_tokens(task_id),
            'quota_limit': self.max_tokens_per_task,
            'usage_percentage': round((used / self.max_tokens_per_task) * 100, 1)
        }
    
    def reset_task(self, task_id: str):
        """Reset token usage for a task."""
        if task_id in self.task_token_usage:
            del self.task_token_usage[task_id]
