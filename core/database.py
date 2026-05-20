"""Unified database layer supporting PostgreSQL and SQLite."""
import json as _json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False


class DatabaseManager:
    """Unified database manager with PostgreSQL primary, SQLite fallback.

    Connection string formats:
        PostgreSQL: postgresql://user:pass@host:5432/dbname
        SQLite:     sqlite:///path/to/db.sqlite3  or just a file path
        Auto:       Falls back to SQLite if no PostgreSQL URL given.
    """

    def __init__(self, db_url: str = ""):
        self.db_url = db_url
        self._conn = None
        self._pg = False
        self._init_connection()

    def _init_connection(self):
        if self.db_url and self.db_url.startswith("postgresql://"):
            if not HAS_POSTGRES:
                raise ImportError(
                    "psycopg2 required for PostgreSQL. "
                    "Install: pip install psycopg2-binary"
                )
            self._conn = psycopg2.connect(
                self.db_url,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            psycopg2.extras.register_default_jsonb(self._conn)
            self._pg = True
        else:
            db_path = self.db_url or "state/orchestrator.db"
            if db_path.startswith("sqlite:///"):
                db_path = db_path[10:]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._pg = False

        self._create_tables()

    def _ph(self, n: int = 1) -> str:
        """Return placeholder string: '?' for SQLite, '%s' for PostgreSQL."""
        return '%s' if self._pg else '?'

    def _ph_list(self, n: int) -> str:
        """Return comma-separated placeholders."""
        ph = self._ph()
        return ', '.join(ph for _ in range(n))

    def _create_tables(self):
        """Create schema if not exists (one statement per execute)."""
        if self._pg:
            statements = [
                """CREATE TABLE IF NOT EXISTS roles (
                    role_id TEXT PRIMARY KEY,
                    data JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )""",
                """CREATE TABLE IF NOT EXISTS instances (
                    instance_id TEXT PRIMARY KEY,
                    data JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_active TIMESTAMP DEFAULT NOW()
                )""",
                """CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'normal',
                    assigned_to TEXT,
                    created_by_role TEXT,
                    delegation_depth INTEGER DEFAULT 0,
                    data JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    approval_required BOOLEAN DEFAULT FALSE,
                    approved_by TEXT,
                    approval_notes TEXT,
                    branch_name TEXT,
                    result_summary TEXT,
                    error_message TEXT,
                    rejection_reason TEXT
                )""",
                """CREATE TABLE IF NOT EXISTS subtasks (
                    subtask_id TEXT PRIMARY KEY,
                    parent_task_id TEXT REFERENCES tasks(task_id),
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    assigned_to TEXT,
                    assigned_by TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'normal',
                    data JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS state_kv (
                    key TEXT PRIMARY KEY,
                    value JSONB DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT NOW()
                )""",
                """CREATE TABLE IF NOT EXISTS activity_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    task_id TEXT,
                    agent_name TEXT,
                    action TEXT,
                    details JSONB DEFAULT '{}'
                )""",
                """CREATE TABLE IF NOT EXISTS cost_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    model TEXT,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    agent_name TEXT,
                    task_id TEXT
                )""",
            ]
            for stmt in statements:
                self._execute_raw(stmt)

            idx_statements = [
                "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
                "CREATE INDEX IF NOT EXISTS idx_subtasks_parent ON subtasks(parent_task_id)",
                "CREATE INDEX IF NOT EXISTS idx_subtasks_status ON subtasks(status)",
                "CREATE INDEX IF NOT EXISTS idx_cost_log_timestamp ON cost_log(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp)",
            ]
            for stmt in idx_statements:
                self._execute_raw(stmt)
        else:
            # SQLite's executescript handles multiple statements
            cur = self._conn.cursor()
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS roles (
                    role_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS instances (
                    instance_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now')),
                    last_active TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'normal',
                    assigned_to TEXT,
                    created_by_role TEXT,
                    delegation_depth INTEGER DEFAULT 0,
                    data TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now')),
                    completed_at TEXT,
                    approval_required INTEGER DEFAULT 0,
                    approved_by TEXT,
                    approval_notes TEXT,
                    branch_name TEXT,
                    result_summary TEXT,
                    error_message TEXT,
                    rejection_reason TEXT
                );
                CREATE TABLE IF NOT EXISTS subtasks (
                    subtask_id TEXT PRIMARY KEY,
                    parent_task_id TEXT REFERENCES tasks(task_id),
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    assigned_to TEXT,
                    assigned_by TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'normal',
                    data TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now')),
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS state_kv (
                    key TEXT PRIMARY KEY,
                    value TEXT DEFAULT '{}',
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    task_id TEXT,
                    agent_name TEXT,
                    action TEXT,
                    details TEXT DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS cost_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    model TEXT,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    agent_name TEXT,
                    task_id TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_subtasks_parent ON subtasks(parent_task_id);
                CREATE INDEX IF NOT EXISTS idx_cost_log_timestamp ON cost_log(timestamp);
            """)
            self._conn.commit()

    def _execute_raw(self, sql: str, params=None):
        """Execute a single SQL statement."""
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        self._conn.commit()

    def _execute(self, sql: str, params=None):
        """Execute SQL and return cursor."""
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        self._conn.commit()
        return cur

    def _fetchone(self, sql: str, params=None) -> Optional[Dict]:
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        row = cur.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return dict(row)

    def _fetchall(self, sql: str, params=None) -> List[Dict]:
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        return [r if isinstance(r, dict) else dict(r) for r in rows]

    def _serialize(self, data: Any) -> str:
        if isinstance(data, str):
            return data
        return _json.dumps(data)

    def _deserialize(self, data: Any) -> Any:
        if isinstance(data, (dict, list)):
            return data
        if isinstance(data, str):
            try:
                return _json.loads(data)
            except (_json.JSONDecodeError, TypeError):
                return data
        return data

    # ── Roles ────────────────────────────────────────────────────────

    def save_role(self, role_id: str, data: dict):
        ser = self._serialize(data)
        if self._pg:
            self._execute_raw(
                """INSERT INTO roles (role_id, data)
                   VALUES (%s, %s)
                   ON CONFLICT (role_id) DO UPDATE
                   SET data = EXCLUDED.data, updated_at = NOW()""",
                (role_id, ser),
            )
        else:
            self._execute_raw(
                """INSERT INTO roles (role_id, data, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(role_id) DO UPDATE
                   SET data = excluded.data, updated_at = datetime('now')""",
                (role_id, ser),
            )

    def get_role(self, role_id: str) -> Optional[dict]:
        row = self._fetchone(
            f"SELECT data FROM roles WHERE role_id={self._ph()}", (role_id,)
        )
        return self._deserialize(row['data']) if row else None

    def get_all_roles(self) -> List[Tuple[str, dict]]:
        rows = self._fetchall("SELECT role_id, data FROM roles")
        return [(r['role_id'], self._deserialize(r['data'])) for r in rows]

    def delete_role(self, role_id: str):
        self._execute_raw(
            f"DELETE FROM roles WHERE role_id={self._ph()}", (role_id,)
        )

    # ── Instances ────────────────────────────────────────────────────

    def save_instance(self, instance_id: str, data: dict):
        ser = self._serialize(data)
        if self._pg:
            self._execute_raw(
                """INSERT INTO instances (instance_id, data)
                   VALUES (%s, %s)
                   ON CONFLICT (instance_id) DO UPDATE
                   SET data = EXCLUDED.data, last_active = NOW()""",
                (instance_id, ser),
            )
        else:
            self._execute_raw(
                """INSERT INTO instances (instance_id, data, last_active)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(instance_id) DO UPDATE
                   SET data = excluded.data, last_active = datetime('now')""",
                (instance_id, ser),
            )

    def get_instance(self, instance_id: str) -> Optional[dict]:
        row = self._fetchone(
            f"SELECT data FROM instances WHERE instance_id={self._ph()}",
            (instance_id,),
        )
        return self._deserialize(row['data']) if row else None

    def get_all_instances(self) -> List[Tuple[str, dict]]:
        rows = self._fetchall("SELECT instance_id, data FROM instances")
        return [(r['instance_id'], self._deserialize(r['data'])) for r in rows]

    def delete_instance(self, instance_id: str):
        self._execute_raw(
            f"DELETE FROM instances WHERE instance_id={self._ph()}", (instance_id,)
        )

    def get_instances_by_role(self, role_id: str) -> List[Tuple[str, dict]]:
        if self._pg:
            rows = self._fetchall(
                "SELECT instance_id, data FROM instances WHERE data->>'role_id'=%s",
                (role_id,),
            )
        else:
            rows = self._fetchall(
                "SELECT instance_id, data FROM instances "
                "WHERE json_extract(data, '$.role_id')=?",
                (role_id,),
            )
        return [(r['instance_id'], self._deserialize(r['data'])) for r in rows]

    # ── Tasks ────────────────────────────────────────────────────────

    def save_task(self, task_id: str, data: dict):
        ser = self._serialize(data.get('data', {}))
        ph = self._ph()
        if self._pg:
            sql = f"""INSERT INTO tasks (task_id, title, description, status, priority,
                        assigned_to, created_by_role, delegation_depth, data,
                        branch_name, result_summary, error_message,
                        rejection_reason, approved_by, approval_notes)
                       VALUES ({self._ph_list(15)})
                       ON CONFLICT (task_id) DO UPDATE SET
                        title = EXCLUDED.title, status = EXCLUDED.status,
                        priority = EXCLUDED.priority, assigned_to = EXCLUDED.assigned_to,
                        data = EXCLUDED.data, branch_name = EXCLUDED.branch_name,
                        result_summary = EXCLUDED.result_summary,
                        error_message = EXCLUDED.error_message,
                        rejection_reason = EXCLUDED.rejection_reason,
                        completed_at = CASE WHEN EXCLUDED.status
                          IN ('completed','failed','approved','rejected')
                          THEN NOW() END"""
        else:
            sql = f"""INSERT INTO tasks (task_id, title, description, status, priority,
                        assigned_to, created_by_role, delegation_depth, data,
                        branch_name, result_summary, error_message,
                        rejection_reason, approved_by, approval_notes)
                       VALUES ({self._ph_list(15)})
                       ON CONFLICT(task_id) DO UPDATE SET
                        title=excluded.title, status=excluded.status,
                        priority=excluded.priority, assigned_to=excluded.assigned_to,
                        data=excluded.data, branch_name=excluded.branch_name,
                        result_summary=excluded.result_summary,
                        error_message=excluded.error_message,
                        rejection_reason=excluded.rejection_reason,
                        completed_at=CASE WHEN excluded.status
                          IN ('completed','failed','approved','rejected')
                          THEN datetime('now') END"""
        self._execute_raw(sql, (
            task_id, data.get('title', ''), data.get('description', ''),
            data.get('status', 'pending'), data.get('priority', 'normal'),
            data.get('assigned_to'), data.get('created_by_role'),
            data.get('delegation_depth', 0), ser,
            data.get('branch_name'), data.get('result_summary'),
            data.get('error_message'), data.get('rejection_reason'),
            data.get('approved_by'), data.get('approval_notes'),
        ))

    def get_task(self, task_id: str) -> Optional[dict]:
        row = self._fetchone(
            f"SELECT * FROM tasks WHERE task_id={self._ph()}", (task_id,)
        )
        return row

    def get_all_tasks(self, status: Optional[str] = None) -> List[dict]:
        if status:
            rows = self._fetchall(
                f"SELECT * FROM tasks WHERE status={self._ph()} "
                "ORDER BY created_at DESC",
                (status,),
            )
        else:
            rows = self._fetchall(
                "SELECT * FROM tasks ORDER BY created_at DESC"
            )
        return rows

    def get_tasks_by_agent(self, agent_id: str) -> List[dict]:
        rows = self._fetchall(
            f"SELECT * FROM tasks WHERE assigned_to={self._ph()} "
            "ORDER BY created_at DESC",
            (agent_id,),
        )
        return rows

    def get_pending_approvals(self) -> List[dict]:
        rows = self._fetchall(
            "SELECT * FROM tasks WHERE status='under_review' ORDER BY created_at"
        )
        return rows

    # ── Subtasks ─────────────────────────────────────────────────────

    def save_subtask(self, subtask_id: str, parent_id: str, data: dict):
        ser = self._serialize(data.get('data', {}))
        ph = self._ph()
        if self._pg:
            sql = f"""INSERT INTO subtasks (subtask_id, parent_task_id, title,
                        description, assigned_to, assigned_by, status, priority, data)
                       VALUES ({self._ph_list(9)})
                       ON CONFLICT (subtask_id) DO UPDATE SET
                        title = EXCLUDED.title, description = EXCLUDED.description,
                        assigned_to = EXCLUDED.assigned_to,
                        assigned_by = EXCLUDED.assigned_by,
                        status = EXCLUDED.status, priority = EXCLUDED.priority,
                        data = EXCLUDED.data"""
        else:
            sql = f"""INSERT OR REPLACE INTO subtasks (subtask_id, parent_task_id,
                        title, description, assigned_to, assigned_by,
                        status, priority, data)
                       VALUES ({self._ph_list(9)})"""
        self._execute_raw(sql, (
            subtask_id, parent_id, data.get('title', ''),
            data.get('description', ''), data.get('assigned_to'),
            data.get('assigned_by'), data.get('status', 'pending'),
            data.get('priority', 'normal'), ser,
        ))

    def get_subtasks(self, parent_id: str) -> List[dict]:
        rows = self._fetchall(
            f"SELECT * FROM subtasks WHERE parent_task_id={self._ph()} "
            "ORDER BY created_at",
            (parent_id,),
        )
        return rows

    # ── State KV ─────────────────────────────────────────────────────

    def set_state(self, key: str, value: Any):
        ser = self._serialize(value)
        ph = self._ph()
        if self._pg:
            self._execute_raw(
                f"""INSERT INTO state_kv (key, value)
                     VALUES ({ph}, {ph})
                     ON CONFLICT (key) DO UPDATE
                     SET value = EXCLUDED.value, updated_at = NOW()""",
                (key, ser),
            )
        else:
            self._execute_raw(
                f"""INSERT OR REPLACE INTO state_kv (key, value, updated_at)
                     VALUES ({ph}, {ph}, datetime('now'))""",
                (key, ser),
            )

    def get_state(self, key: str, default: Any = None) -> Any:
        row = self._fetchone(
            f"SELECT value FROM state_kv WHERE key={self._ph()}", (key,)
        )
        return self._deserialize(row['value']) if row else default

    # ── Activity Log ─────────────────────────────────────────────────

    def log_activity(self, task_id: str, agent_name: str,
                     action: str, details: dict = None):
        ph = self._ph_list(4)
        self._execute_raw(
            "INSERT INTO activity_log (task_id, agent_name, action, details) "
            f"VALUES ({ph})",
            (task_id, agent_name, action, self._serialize(details or {})),
        )

    def get_activities(self, limit: int = 100) -> List[dict]:
        rows = self._fetchall(
            f"SELECT * FROM activity_log ORDER BY timestamp DESC "
            f"LIMIT {self._ph()}",
            (limit,),
        )
        return rows

    # ── Cost Tracking ────────────────────────────────────────────────

    def record_cost(self, model: str, prompt_tokens: int,
                    completion_tokens: int, total_tokens: int,
                    cost: float, agent_name: str = "", task_id: str = ""):
        self._execute_raw(
            "INSERT INTO cost_log (model, prompt_tokens, completion_tokens, "
            f"total_tokens, cost, agent_name, task_id) "
            f"VALUES ({self._ph_list(7)})",
            (model, prompt_tokens, completion_tokens,
             total_tokens, cost, agent_name, task_id),
        )

    def get_daily_cost(self, date: Optional[str] = None) -> dict:
        from datetime import datetime
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        ph = self._ph()
        if self._pg:
            row = self._fetchone(
                "SELECT SUM(cost) as total_cost, COUNT(*) as total_requests, "
                "SUM(total_tokens) as total_tokens "
                "FROM cost_log WHERE date(timestamp)=%s",
                (date,),
            )
        else:
            row = self._fetchone(
                "SELECT SUM(cost) as total_cost, COUNT(*) as total_requests, "
                "SUM(total_tokens) as total_tokens "
                "FROM cost_log WHERE date(timestamp)=?",
                (date,),
            )
        return row if row else {'total_cost': 0, 'total_requests': 0,
                                'total_tokens': 0}

    def get_cost_summary(self, days: int = 7) -> dict:
        ph = self._ph()
        if self._pg:
            rows = self._fetchall(
                "SELECT date(timestamp) as day, SUM(cost) as total_cost, "
                "COUNT(*) as requests, SUM(total_tokens) as tokens "
                "FROM cost_log "
                "WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day' * %s "
                "GROUP BY day ORDER BY day",
                (days,),
            )
        else:
            rows = self._fetchall(
                "SELECT date(timestamp) as day, SUM(cost) as total_cost, "
                "COUNT(*) as requests, SUM(total_tokens) as tokens "
                "FROM cost_log "
                f"WHERE timestamp >= datetime('now', {ph}) "
                "GROUP BY day ORDER BY day",
                (f'-{days} days',),
            )
        total_cost = sum(r['total_cost'] or 0 for r in rows)
        total_requests = sum(r['requests'] or 0 for r in rows)
        total_tokens = sum(r['tokens'] or 0 for r in rows)
        return {
            'total_cost': total_cost,
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'daily_breakdown': rows,
        }

    # ── Stats ────────────────────────────────────────────────────────

    def get_task_stats(self) -> dict:
        stats = {}
        statuses = ['pending', 'assigned', 'in_progress', 'delegated',
                    'under_review', 'completed', 'failed', 'rejected']
        ph = self._ph()
        for status in statuses:
            row = self._fetchone(
                f"SELECT COUNT(*) as cnt FROM tasks WHERE status={ph}",
                (status,),
            )
            stats[status] = row['cnt'] if row else 0

        total_row = self._fetchone("SELECT COUNT(*) as cnt FROM tasks")
        stats['total_tasks'] = total_row['cnt'] if total_row else 0

        sub_row = self._fetchone("SELECT COUNT(*) as cnt FROM subtasks")
        stats['total_subtasks'] = sub_row['cnt'] if sub_row else 0

        return stats

    def close(self):
        if self._conn:
            self._conn.close()
