"""
SupportAI-Env — Database Layer
Persistent storage for sessions, users, analytics, and leaderboards
Supports SQLite (default) and PostgreSQL
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import threading

# ─── Data Models ────────────────────────────────────────────────────────────

@dataclass
class SessionRecord:
    session_id: str
    user_id: Optional[str]
    task_id: str
    status: str  # active | completed | failed
    start_time: float
    end_time: Optional[float]
    final_score: float
    grade_label: str
    step_count: int
    total_reward: float
    action_history: str  # JSON
    state_history: str   # JSON
    metadata: str  # JSON
    created_at: str

@dataclass
class UserRecord:
    user_id: str
    username: str
    email: str
    created_at: str
    last_login: Optional[str]
    total_sessions: int
    avg_score: float

@dataclass
class AnalyticsRecord:
    record_id: str
    user_id: Optional[str]
    task_id: str
    metric_name: str
    metric_value: float
    timestamp: str

# ─── Database Manager ───────────────────────────────────────────────────────

class DatabaseManager:
    """
    Manages all database operations with thread-safe connections.
    Supports SQLite (default) and PostgreSQL.
    """
    
    def __init__(self, db_path: str = "supportai.db"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._initialize_db()
    
    def _initialize_db(self):
        """Create tables if they don't exist."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    final_score REAL,
                    grade_label TEXT,
                    step_count INTEGER,
                    total_reward REAL,
                    action_history TEXT,
                    state_history TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    total_sessions INTEGER DEFAULT 0,
                    avg_score REAL DEFAULT 0.0,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    record_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    task_id TEXT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            
            # Leaderboard cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard (
                    rank INTEGER PRIMARY KEY,
                    user_id TEXT,
                    username TEXT,
                    avg_score REAL,
                    total_sessions INTEGER,
                    last_updated TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            
            conn.commit()
            conn.close()
    
    # ─── Session Operations ──────────────────────────────────────────────────
    
    def create_session(
        self,
        session_id: str,
        task_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> SessionRecord:
        """Create a new session record."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            start_time = time.time()
            
            cursor.execute("""
                INSERT INTO sessions
                (session_id, user_id, task_id, status, start_time, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                task_id,
                "active",
                start_time,
                now,
                json.dumps(metadata or {})
            ))
            
            conn.commit()
            conn.close()
            
            return SessionRecord(
                session_id=session_id,
                user_id=user_id,
                task_id=task_id,
                status="active",
                start_time=start_time,
                end_time=None,
                final_score=0.0,
                grade_label="",
                step_count=0,
                total_reward=0.0,
                action_history="[]",
                state_history="[]",
                metadata=json.dumps(metadata or {}),
                created_at=now
            )
    
    def update_session(
        self,
        session_id: str,
        status: str,
        final_score: float = 0.0,
        grade_label: str = "",
        step_count: int = 0,
        total_reward: float = 0.0,
        action_history: Optional[List] = None,
        state_history: Optional[List] = None
    ):
        """Update session with completion info."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sessions
                SET status=?, end_time=?, final_score=?, grade_label=?,
                    step_count=?, total_reward=?, action_history=?, state_history=?
                WHERE session_id=?
            """, (
                status,
                time.time() if status == "completed" else None,
                final_score,
                grade_label,
                step_count,
                total_reward,
                json.dumps(action_history or []),
                json.dumps(state_history or []),
                session_id
            ))
            
            conn.commit()
            conn.close()
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve session by ID."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM sessions WHERE session_id=?
            """, (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            cols = [desc[0] for desc in cursor.description]
            return dict(zip(cols, row))
    
    def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all sessions for a user."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM sessions
                WHERE user_id=?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            conn.close()
            
            return [dict(zip(cols, row)) for row in rows]
    
    # ─── User Operations ────────────────────────────────────────────────────
    
    def create_user(
        self,
        user_id: str,
        username: str,
        email: Optional[str] = None,
        password_hash: Optional[str] = None
    ) -> UserRecord:
        """Create a new user."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO users
                (user_id, username, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, email, password_hash, now))
            
            conn.commit()
            conn.close()
            
            return UserRecord(
                user_id=user_id,
                username=username,
                email=email or "",
                created_at=now,
                last_login=None,
                total_sessions=0,
                avg_score=0.0
            )
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM users WHERE user_id=?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            cols = [desc[0] for desc in cursor.description]
            return dict(zip(cols, row))
    
    def update_user_stats(self, user_id: str):
        """Recalculate user stats from sessions."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT AVG(final_score) as avg_score, COUNT(*) as total_sessions
                FROM sessions
                WHERE user_id=? AND status='completed'
            """, (user_id,))
            
            row = cursor.fetchone()
            avg_score = row[0] or 0.0
            total_sessions = row[1] or 0
            
            cursor.execute("""
                UPDATE users
                SET avg_score=?, total_sessions=?, last_login=?
                WHERE user_id=?
            """, (avg_score, total_sessions, datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
    
    # ─── Analytics Operations ───────────────────────────────────────────────
    
    def record_metric(
        self,
        record_id: str,
        metric_name: str,
        metric_value: float,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None
    ):
        """Record an analytics metric."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO analytics
                (record_id, user_id, task_id, metric_name, metric_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record_id,
                user_id,
                task_id,
                metric_name,
                metric_value,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
    
    def get_metrics(
        self,
        metric_name: Optional[str] = None,
        user_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict]:
        """Get metrics from last N hours."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            query = "SELECT * FROM analytics WHERE timestamp > ?"
            params = [cutoff]
            
            if user_id:
                query += " AND user_id=?"
                params.append(user_id)
            if metric_name:
                query += " AND metric_name=?"
                params.append(metric_name)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            conn.close()
            
            return [dict(zip(cols, row)) for row in rows]
    
    # ─── Leaderboard Operations ────────────────────────────────────────────
    
    def refresh_leaderboard(self, limit: int = 100):
        """Refresh leaderboard rankings."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get top users by average score
            cursor.execute("""
                SELECT u.user_id, u.username, u.avg_score, u.total_sessions
                FROM users u
                WHERE u.is_active=1 AND u.total_sessions > 0
                ORDER BY u.avg_score DESC, u.total_sessions DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            # Clear old leaderboard
            cursor.execute("DELETE FROM leaderboard")
            
            # Insert new rankings
            for rank, (user_id, username, avg_score, total_sessions) in enumerate(rows, 1):
                cursor.execute("""
                    INSERT INTO leaderboard
                    (rank, user_id, username, avg_score, total_sessions, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    rank,
                    user_id,
                    username,
                    avg_score,
                    total_sessions,
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
    
    def get_leaderboard(self, limit: int = 50) -> List[Dict]:
        """Get current leaderboard."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM leaderboard
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            conn.close()
            
            return [dict(zip(cols, row)) for row in rows]


# Global instance
db = DatabaseManager()
