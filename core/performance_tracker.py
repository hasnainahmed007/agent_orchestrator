"""Agent performance metrics and reporting."""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field


@dataclass
class AgentMetrics:
    """Performance metrics for a single agent."""
    agent_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_execution_time: float = 0.0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    avg_execution_time: float = 0.0
    success_rate: float = 0.0
    last_active: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def update(self, success: bool, execution_time: float, tokens: int, cost: float):
        """Update metrics with new task result."""
        self.total_tasks += 1
        
        if success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1
        
        self.total_execution_time += execution_time
        self.total_tokens_used += tokens
        self.total_cost += cost
        self.last_active = datetime.now().isoformat()
        
        self.avg_execution_time = self.total_execution_time / max(1, self.total_tasks)
        self.success_rate = (self.successful_tasks / max(1, self.total_tasks)) * 100


@dataclass
class TaskMetrics:
    """Metrics for a single task."""
    task_id: str
    description: str
    status: str
    started_at: str
    completed_at: str
    execution_time: float
    agents_used: List[str]
    files_created: int = 0
    files_modified: int = 0
    tokens_used: int = 0
    cost: float = 0.0
    validation_passed: bool = True
    approval_required: bool = True
    approved: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)


class PerformanceTracker:
    """Tracks and reports on agent and system performance."""
    
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.state_dir / 'performance_metrics.json'
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.task_metrics: Dict[str, TaskMetrics] = {}
        self._load()
    
    def _load(self):
        """Load metrics from file."""
        if self.metrics_file.exists():
            try:
                data = json.loads(self.metrics_file.read_text())
                
                for agent_name, metrics_data in data.get('agent_metrics', {}).items():
                    self.agent_metrics[agent_name] = AgentMetrics(**metrics_data)
                
                for task_id, metrics_data in data.get('task_metrics', {}).items():
                    self.task_metrics[task_id] = TaskMetrics(**metrics_data)
            except:
                self.agent_metrics = {}
                self.task_metrics = {}
    
    def _save(self):
        """Save metrics to file."""
        data = {
            'agent_metrics': {
                name: metrics.to_dict()
                for name, metrics in self.agent_metrics.items()
            },
            'task_metrics': {
                task_id: metrics.to_dict()
                for task_id, metrics in self.task_metrics.items()
            },
            'last_updated': datetime.now().isoformat()
        }
        self.metrics_file.write_text(json.dumps(data, indent=2))
    
    def record_task_start(self, task_id: str, description: str, agents: List[str]):
        """Record task start."""
        self.task_metrics[task_id] = TaskMetrics(
            task_id=task_id,
            description=description,
            status="running",
            started_at=datetime.now().isoformat(),
            completed_at="",
            execution_time=0.0,
            agents_used=agents
        )
        self._save()
    
    def record_task_complete(self, task_id: str, success: bool, files_created: int = 0,
                            files_modified: int = 0, tokens_used: int = 0, cost: float = 0.0,
                            validation_passed: bool = True, approved: bool = False):
        """Record task completion."""
        if task_id not in self.task_metrics:
            return
        
        task = self.task_metrics[task_id]
        task.completed_at = datetime.now().isoformat()
        task.status = "completed" if success else "failed"
        task.files_created = files_created
        task.files_modified = files_modified
        task.tokens_used = tokens_used
        task.cost = cost
        task.validation_passed = validation_passed
        task.approved = approved
        
        started = datetime.fromisoformat(task.started_at)
        completed = datetime.fromisoformat(task.completed_at)
        task.execution_time = (completed - started).total_seconds()
        
        for agent_name in task.agents_used:
            if agent_name not in self.agent_metrics:
                self.agent_metrics[agent_name] = AgentMetrics(agent_name=agent_name)
            
            self.agent_metrics[agent_name].update(
                success=success,
                execution_time=task.execution_time / max(1, len(task.agents_used)),
                tokens=tokens_used // max(1, len(task.agents_used)),
                cost=cost / max(1, len(task.agents_used))
            )
        
        self._save()
    
    def get_agent_performance(self, agent_name: str) -> Optional[Dict]:
        """Get performance metrics for an agent."""
        metrics = self.agent_metrics.get(agent_name)
        if not metrics:
            return None
        
        return metrics.to_dict()
    
    def get_all_agents_performance(self) -> List[Dict]:
        """Get performance metrics for all agents."""
        return [
            metrics.to_dict()
            for metrics in self.agent_metrics.values()
        ]
    
    def get_task_performance(self, task_id: str) -> Optional[Dict]:
        """Get performance metrics for a task."""
        task = self.task_metrics.get(task_id)
        if not task:
            return None
        
        return task.to_dict()
    
    def get_system_summary(self, days: int = 7) -> Dict:
        """Get system-wide performance summary."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        recent_tasks = [
            task for task in self.task_metrics.values()
            if task.started_at >= cutoff
        ]
        
        total_tasks = len(recent_tasks)
        successful = sum(1 for t in recent_tasks if t.status == "completed")
        failed = total_tasks - successful
        
        total_time = sum(t.execution_time for t in recent_tasks)
        total_cost = sum(t.cost for t in recent_tasks)
        total_tokens = sum(t.tokens_used for t in recent_tasks)
        
        avg_time = total_time / max(1, total_tasks)
        success_rate = (successful / max(1, total_tasks)) * 100
        
        return {
            'period_days': days,
            'total_tasks': total_tasks,
            'successful_tasks': successful,
            'failed_tasks': failed,
            'success_rate': round(success_rate, 1),
            'avg_execution_time_seconds': round(avg_time, 1),
            'total_execution_time_seconds': round(total_time, 1),
            'total_cost': round(total_cost, 6),
            'total_tokens_used': total_tokens,
            'total_files_created': sum(t.files_created for t in recent_tasks),
            'total_files_modified': sum(t.files_modified for t in recent_tasks),
            'active_agents': len(self.agent_metrics)
        }
    
    def get_top_performing_agents(self, limit: int = 5) -> List[Dict]:
        """Get top performing agents by success rate."""
        agents = [
            metrics.to_dict()
            for metrics in self.agent_metrics.values()
            if metrics.total_tasks > 0
        ]
        
        agents.sort(key=lambda x: x['success_rate'], reverse=True)
        
        return agents[:limit]
    
    def get_slowest_tasks(self, limit: int = 10) -> List[Dict]:
        """Get slowest tasks."""
        tasks = [
            task.to_dict()
            for task in self.task_metrics.values()
            if task.execution_time > 0
        ]
        
        tasks.sort(key=lambda x: x['execution_time'], reverse=True)
        
        return tasks[:limit]
    
    def get_most_expensive_tasks(self, limit: int = 10) -> List[Dict]:
        """Get most expensive tasks."""
        tasks = [
            task.to_dict()
            for task in self.task_metrics.values()
            if task.cost > 0
        ]
        
        tasks.sort(key=lambda x: x['cost'], reverse=True)
        
        return tasks[:limit]
    
    def export_report(self, days: int = 30) -> str:
        """Export performance report."""
        summary = self.get_system_summary(days)
        agents = self.get_all_agents_performance()
        
        report = [
            "=" * 60,
            "PERFORMANCE REPORT",
            f"Period: Last {days} days",
            "=" * 60,
            "",
            "SYSTEM SUMMARY",
            "-" * 40,
            f"Total Tasks: {summary['total_tasks']}",
            f"Success Rate: {summary['success_rate']}%",
            f"Avg Execution Time: {summary['avg_execution_time_seconds']}s",
            f"Total Cost: ${summary['total_cost']:.6f}",
            f"Total Tokens: {summary['total_tokens_used']:,}",
            "",
            "AGENT PERFORMANCE",
            "-" * 40
        ]
        
        for agent in agents:
            report.append(
                f"\n{agent['agent_name']}:"
                f"\n  Tasks: {agent['total_tasks']}"
                f"\n  Success Rate: {agent['success_rate']:.1f}%"
                f"\n  Avg Time: {agent['avg_execution_time']:.1f}s"
                f"\n  Total Cost: ${agent['total_cost']:.6f}"
            )
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def reset(self):
        """Reset all metrics."""
        self.agent_metrics = {}
        self.task_metrics = {}
        self._save()
