"""
SupportAI-Env — Advanced Analytics Module
Performance trends, insights, batch statistics, and export capabilities
"""

import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import uuid

from database import db

# ─── Analytics Engine ───────────────────────────────────────────────────────

class AnalyticsEngine:
    """
    Comprehensive analytics for sessions, users, and performance trends.
    """
    
    def __init__(self):
        self.cache = {}
    
    # ─── Session Analytics ──────────────────────────────────────────────────
    
    def analyze_session(self, session_data: Dict) -> Dict:
        """Analyze a single session."""
        action_history = json.loads(session_data.get("action_history", "[]"))
        
        return {
            "session_id": session_data["session_id"],
            "task_id": session_data["task_id"],
            "duration_seconds": round((session_data.get("end_time") or 0) - session_data["start_time"], 2),
            "step_count": session_data.get("step_count", 0),
            "final_score": session_data.get("final_score", 0.0),
            "grade_label": session_data.get("grade_label", ""),
            "total_reward": session_data.get("total_reward", 0.0),
            "actions": action_history,
            "action_frequencies": self._count_actions(action_history),
            "efficiency_score": self._calculate_efficiency(
                session_data.get("step_count", 0),
                session_data.get("final_score", 0.0)
            )
        }
    
    def analyze_user(self, user_id: str) -> Dict:
        """Comprehensive user performance analysis."""
        sessions = db.get_user_sessions(user_id, limit=200)
        
        if not sessions:
            return {
                "user_id": user_id,
                "total_sessions": 0,
                "avg_score": 0.0,
                "trend": "neutral"
            }
        
        completed_sessions = [s for s in sessions if s.get("status") == "completed"]
        
        if not completed_sessions:
            return {
                "user_id": user_id,
                "total_sessions": len(sessions),
                "complete_rate": 0.0,
                "avg_score": 0.0
            }
        
        scores = [s.get("final_score", 0.0) for s in completed_sessions]
        steps = [s.get("step_count", 0) for s in completed_sessions]
        
        return {
            "user_id": user_id,
            "total_sessions": len(sessions),
            "completed_sessions": len(completed_sessions),
            "completion_rate": round(len(completed_sessions) / len(sessions) * 100, 2),
            "avg_score": round(statistics.mean(scores), 4),
            "median_score": round(statistics.median(scores), 4),
            "std_dev_score": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0,
            "avg_steps": round(statistics.mean(steps), 2),
            "best_score": round(max(scores), 4),
            "worst_score": round(min(scores), 4),
            "task_distribution": self._get_task_distribution(completed_sessions),
            "grade_distribution": self._get_grade_distribution(completed_sessions),
            "trend": self._calculate_trend(completed_sessions[-10:]),  # Last 10
            "improvement": self._calculate_improvement(completed_sessions)
        }
    
    def task_performance_report(self, task_id: str) -> Dict:
        """Analyze performance across all users for a task."""
        sessions = db.get_user_sessions(None, limit=1000)  # Get many sessions
        task_sessions = [s for s in sessions if s.get("task_id") == task_id and s.get("status") == "completed"]
        
        if not task_sessions:
            return {
                "task_id": task_id,
                "total_attempts": 0,
                "avg_score": 0.0
            }
        
        scores = [s.get("final_score", 0.0) for s in task_sessions]
        steps = [s.get("step_count", 0) for s in task_sessions]
        
        return {
            "task_id": task_id,
            "total_attempts": len(task_sessions),
            "success_rate": round(
                len([s for s in task_sessions if s.get("grade_label") in ("full", "partial")]) / len(task_sessions) * 100,
                2
            ),
            "avg_score": round(statistics.mean(scores), 4),
            "median_score": round(statistics.median(scores), 4),
            "std_dev": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0,
            "avg_steps": round(statistics.mean(steps), 2),
            "difficulty_level": self._categorize_difficulty(statistics.mean(scores)),
            "grade_distribution": self._count_grades(task_sessions)
        }
    
    # ─── Private Helper Methods ──────────────────────────────────────────────
    
    def _count_actions(self, action_list: List[str]) -> Dict[str, int]:
        """Count action frequencies."""
        counts = defaultdict(int)
        for action in action_list:
            counts[action] += 1
        return dict(counts)
    
    def _calculate_efficiency(self, step_count: int, score: float) -> float:
        """Calculate efficiency score (score per step)."""
        if step_count == 0:
            return 0.0
        return round(score / step_count, 4)
    
    def _get_task_distribution(self, sessions: List[Dict]) -> Dict[str, int]:
        """Get distribution of tasks."""
        dist = defaultdict(int)
        for session in sessions:
            dist[session.get("task_id", "unknown")] += 1
        return dict(dist)
    
    def _get_grade_distribution(self, sessions: List[Dict]) -> Dict[str, int]:
        """Get distribution of grades."""
        dist = defaultdict(int)
        for session in sessions:
            grade = session.get("grade_label", "unknown")
            dist[grade] += 1
        return dict(dist)
    
    def _calculate_trend(self, recent_sessions: List[Dict]) -> str:
        """Calculate performance trend."""
        if len(recent_sessions) < 2:
            return "neutral"
        
        scores = [s.get("final_score", 0.0) for s in recent_sessions]
        first_half_avg = statistics.mean(scores[:len(scores)//2])
        second_half_avg = statistics.mean(scores[len(scores)//2:])
        
        diff = second_half_avg - first_half_avg
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        return "stable"
    
    def _calculate_improvement(self, all_sessions: List[Dict]) -> Dict:
        """Calculate improvement metrics."""
        if len(all_sessions) < 2:
            return {"week_over_week": 0, "overall": 0}
        
        scores = [s.get("final_score", 0.0) for s in all_sessions]
        
        # Split into first and second half
        mid = len(scores) // 2
        first_avg = statistics.mean(scores[:mid]) if mid > 0 else scores[0]
        second_avg = statistics.mean(scores[mid:])
        
        improvement = round(((second_avg - first_avg) / (first_avg or 0.01)) * 100, 2)
        
        return {
            "percentage": improvement,
            "direction": "up" if improvement > 0 else "down" if improvement < 0 else "stable"
        }
    
    def _categorize_difficulty(self, avg_score: float) -> str:
        """Categorize task difficulty from average score."""
        if avg_score >= 0.85:
            return "easy"
        elif avg_score >= 0.65:
            return "medium"
        else:
            return "hard"
    
    def _count_grades(self, sessions: List[Dict]) -> Dict[str, int]:
        """Count grade distribution."""
        counts = defaultdict(int)
        for session in sessions:
            grade = session.get("grade_label", "unknown")
            counts[grade] += 1
        return dict(counts)


# ─── Data Export Module ────────────────────────────────────────────────────

class DataExporter:
    """Export session and analytics data in various formats."""
    
    @staticmethod
    def to_csv(data: List[Dict]) -> str:
        """Export data to CSV format."""
        if not data:
            return ""
        
        headers = list(data[0].keys())
        lines = [",".join(headers)]
        
        for row in data:
            values = []
            for header in headers:
                val = str(row.get(header, ""))
                # Escape quotes and commas
                if "," in val or '"' in val:
                    val = f'"{val.replace('"', '""')}"'
                values.append(val)
            lines.append(",".join(values))
        
        return "\n".join(lines)
    
    @staticmethod
    def to_json(data) -> str:
        """Export data to JSON format."""
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def generate_report(user_id: str, include_sessions: bool = True) -> Dict:
        """Generate comprehensive user report."""
        engine = AnalyticsEngine()
        user_data = db.get_user(user_id)
        
        if not user_data:
            return {"error": "User not found"}
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "user_id": user_id,
            "username": user_data.get("username"),
            "analysis": engine.analyze_user(user_id),
        }
        
        if include_sessions:
            sessions = db.get_user_sessions(user_id, limit=100)
            report["sessions"] = [engine.analyze_session(s) for s in sessions]
        
        return report


# Instances
analytics = AnalyticsEngine()
exporter = DataExporter()
