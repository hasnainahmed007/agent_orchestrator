"""Cost tracking for API usage and agent operations."""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass, asdict, field


@dataclass
class TokenUsage:
    """Track token usage for a single request."""
    timestamp: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    agent_name: str = ""
    task_id: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DailyBudget:
    """Track daily budget usage."""
    date: str
    total_cost: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


class CostTracker:
    """Tracks API costs and usage for all agent operations."""
    
    OPENAI_PRICES = {
        'gpt-4o': {'input': 5.00, 'output': 15.00},
        'gpt-4o-mini': {'input': 0.150, 'output': 0.600},
        'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
        'gpt-4': {'input': 30.00, 'output': 60.00},
        'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},
    }
    
    def __init__(self, state_dir: Path, daily_budget_limit: float = 5.0):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.cost_file = self.state_dir / 'cost_tracking.json'
        self.daily_budget_limit = daily_budget_limit
        self.usage_log: List[Dict] = []
        self.daily_budgets: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        """Load cost tracking data."""
        if self.cost_file.exists():
            try:
                data = json.loads(self.cost_file.read_text())
                self.usage_log = data.get('usage_log', [])
                self.daily_budgets = data.get('daily_budgets', {})
            except:
                self.usage_log = []
                self.daily_budgets = {}
    
    def _save(self):
        """Save cost tracking data."""
        data = {
            'usage_log': self.usage_log[-1000:],
            'daily_budgets': self.daily_budgets
        }
        self.cost_file.write_text(json.dumps(data, indent=2))
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for token usage."""
        prices = self.OPENAI_PRICES.get(model, {'input': 5.00, 'output': 15.00})
        
        input_cost = (prompt_tokens / 1_000_000) * prices['input']
        output_cost = (completion_tokens / 1_000_000) * prices['output']
        
        return round(input_cost + output_cost, 6)
    
    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int, 
                    agent_name: str = "", task_id: str = "") -> float:
        """Record API usage. Returns calculated cost.

        Args:
            model: Model name used
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            agent_name: Name of agent making the request
            task_id: Associated task ID
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
        
        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            agent_name=agent_name,
            task_id=task_id
        )
        
        self.usage_log.append(usage.to_dict())
        
        self._update_daily_budget(cost, total_tokens)
        self._save()

        return cost
    
    def _update_daily_budget(self, cost: float, tokens: int):
        """Update daily budget tracking."""
        today = date.today().isoformat()
        
        if today not in self.daily_budgets:
            self.daily_budgets[today] = {
                'date': today,
                'total_cost': 0.0,
                'total_requests': 0,
                'total_tokens': 0
            }
        
        budget = self.daily_budgets[today]
        budget['total_cost'] = round(budget['total_cost'] + cost, 6)
        budget['total_requests'] += 1
        budget['total_tokens'] += tokens
    
    def is_within_budget(self) -> bool:
        """Check if current day's usage is within budget."""
        today = date.today().isoformat()
        budget = self.daily_budgets.get(today, {})
        return budget.get('total_cost', 0.0) < self.daily_budget_limit
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget for today."""
        today = date.today().isoformat()
        budget = self.daily_budgets.get(today, {})
        spent = budget.get('total_cost', 0.0)
        return round(max(0, self.daily_budget_limit - spent), 6)
    
    def get_daily_usage(self, day: Optional[str] = None) -> Dict:
        """Get usage for a specific day."""
        target_day = day or date.today().isoformat()
        return self.daily_budgets.get(target_day, {
            'date': target_day,
            'total_cost': 0.0,
            'total_requests': 0,
            'total_tokens': 0
        })
    
    def get_usage_summary(self, days: int = 7) -> Dict:
        """Get usage summary for last N days.
        
        Args:
            days: Number of days to summarize
            
        Returns:
            Summary dictionary
        """
        from datetime import timedelta
        
        today = date.today()
        summary = {
            'total_cost': 0.0,
            'total_requests': 0,
            'total_tokens': 0,
            'daily_breakdown': [],
            'period_days': days
        }
        
        for i in range(days):
            day = (today - timedelta(days=i)).isoformat()
            budget = self.daily_budgets.get(day, {
                'total_cost': 0.0,
                'total_requests': 0,
                'total_tokens': 0
            })
            
            summary['total_cost'] += budget.get('total_cost', 0.0)
            summary['total_requests'] += budget.get('total_requests', 0)
            summary['total_tokens'] += budget.get('total_tokens', 0)
            
            summary['daily_breakdown'].append({
                'date': day,
                'cost': budget.get('total_cost', 0.0),
                'requests': budget.get('total_requests', 0),
                'tokens': budget.get('total_tokens', 0)
            })
        
        summary['total_cost'] = round(summary['total_cost'], 6)
        summary['daily_breakdown'].reverse()
        
        return summary
    
    def get_task_costs(self, task_id: str) -> Dict:
        """Get all costs associated with a specific task."""
        task_usages = [u for u in self.usage_log if u.get('task_id') == task_id]
        
        total_cost = sum(u.get('cost', 0) for u in task_usages)
        total_tokens = sum(u.get('total_tokens', 0) for u in task_usages)
        
        return {
            'task_id': task_id,
            'total_cost': round(total_cost, 6),
            'total_requests': len(task_usages),
            'total_tokens': total_tokens,
            'usages': task_usages
        }
    
    def get_agent_costs(self, agent_name: str, days: int = 7) -> Dict:
        """Get costs for a specific agent."""
        from datetime import timedelta
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        agent_usages = [
            u for u in self.usage_log 
            if u.get('agent_name') == agent_name and u.get('timestamp') >= cutoff
        ]
        
        total_cost = sum(u.get('cost', 0) for u in agent_usages)
        total_tokens = sum(u.get('total_tokens', 0) for u in agent_usages)
        
        return {
            'agent_name': agent_name,
            'period_days': days,
            'total_cost': round(total_cost, 6),
            'total_requests': len(agent_usages),
            'total_tokens': total_tokens,
            'avg_cost_per_request': round(total_cost / max(1, len(agent_usages)), 6)
        }
    
    def reset_daily_budget(self, new_limit: Optional[float] = None):
        """Reset daily budget limit."""
        if new_limit is not None:
            self.daily_budget_limit = new_limit
        
        today = date.today().isoformat()
        if today in self.daily_budgets:
            self.daily_budgets[today] = {
                'date': today,
                'total_cost': 0.0,
                'total_requests': 0,
                'total_tokens': 0
            }
            self._save()
    
    def export_report(self, days: int = 30) -> str:
        """Export cost report as formatted string."""
        summary = self.get_usage_summary(days)
        
        report = [
            "=" * 60,
            "COST TRACKING REPORT",
            f"Period: Last {days} days",
            "=" * 60,
            "",
            f"Total Cost: ${summary['total_cost']:.6f}",
            f"Total Requests: {summary['total_requests']}",
            f"Total Tokens: {summary['total_tokens']:,}",
            "",
            "Daily Breakdown:",
            "-" * 40
        ]
        
        for day in summary['daily_breakdown']:
            report.append(
                f"  {day['date']}: ${day['cost']:.6f} "
                f"({day['requests']} requests, {day['tokens']:,} tokens)"
            )
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
