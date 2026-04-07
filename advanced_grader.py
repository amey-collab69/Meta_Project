"""
SupportAI-Env — Advanced Grader with Custom Rubrics
Weighted scoring, A/B testing support, detailed feedback, and performance analysis
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ScoringRubric:
    """Custom rubric for task evaluation."""
    name: str
    criteria: Dict[str, float]  # criterion_name -> weight
    threshold_excellent: float = 0.85
    threshold_good: float = 0.65
    threshold_acceptable: float = 0.40


class AdvancedGrader:
    """
    Enhanced grading system with:
    - Weighted scoring based on custom rubrics
    - Detailed feedback
    - A/B testing support
    - Performance analytics
    """
    
    def __init__(self):
        # Default rubrics for each task
        self.rubrics = {
            "easy": self._create_easy_rubric(),
            "medium": self._create_medium_rubric(),
            "hard": self._create_hard_rubric(),
        }
    
    def _create_easy_rubric(self) -> ScoringRubric:
        """Rubric for easy tasks (order status)."""
        return ScoringRubric(
            name="Easy Task - Order Status",
            criteria={
                "intent_detection": 0.20,
                "appropriate_response": 0.25,
                "resolution_speed": 0.15,
                "tone_appropriate": 0.15,
                "action_sequence": 0.25
            }
        )
    
    def _create_medium_rubric(self) -> ScoringRubric:
        """Rubric for medium tasks (refund flow)."""
        return ScoringRubric(
            name="Medium Task - Refund Flow",
            criteria={
                "intent_detection": 0.20,
                "validation": 0.20,
                "empathy": 0.15,
                "correct_resolution": 0.25,
                "compliance_check": 0.20
            }
        )
    
    def _create_hard_rubric(self) -> ScoringRubric:
        """Rubric for hard tasks (angry multi-issue)."""
        return ScoringRubric(
            name="Hard Task - Angry Customer",
            criteria={
                "emotion_recognition": 0.25,
                "de_escalation": 0.25,
                "multi_issue_handling": 0.20,
                "resolution_quality": 0.20,
                "follow_up": 0.10
            }
        )
    
    def grade_comprehensive(
        self,
        task: Dict,
        action_history: List[str],
        total_reward: float,
        final_state: str,
        step_count: int,
        intent_detected: str,
        tone: str,
        conversation_history: Optional[List[str]] = None,
        sentiment_trend: Optional[List[str]] = None
    ) -> Dict:
        """
        Advanced grading with detailed breakdown and feedback.
        """
        task_id = task.get("id", "unknown")
        rubric = self.rubrics.get(task_id, self.rubrics["easy"])
        
        expected_workflow = task.get("expected_workflow", [])
        expected_intent = task.get("expected_intent", "any")
        max_steps = task.get("max_steps", 10)
        
        # Calculate individual criteria scores
        criteria_scores = {}
        
        # 1. Intent Detection (20%)
        intent_correct = (intent_detected == expected_intent or expected_intent == "any")
        criteria_scores["intent_detection"] = 1.0 if intent_correct else 0.5
        
        # 2. Action Sequence (20-25%)
        seq_score = self._score_sequence(action_history, expected_workflow)
        criteria_scores["action_sequence"] = seq_score
        
        # 3. Resolution (20%)
        resolved = final_state in ("RESOLUTION", "END")
        criteria_scores["resolution_quality"] = 1.0 if resolved else 0.0
        
        # 4. Efficiency (15%)
        efficiency = self._score_efficiency(step_count, max_steps)
        criteria_scores["resolution_speed"] = efficiency
        
        # 5. Tone Handling (15%)
        tone_score = self._score_tone_handling(tone, task.get("requires_tone_handling", False))
        criteria_scores["tone_appropriate"] = tone_score
        criteria_scores["de_escalation"] = tone_score
        criteria_scores["emotion_recognition"] = tone_score
        
        # 6. Reward-based score (supportive)
        reward_score = min(1.0, max(0.0, total_reward / 10.0))  # Normalize to 0-1
        
        # Additional criteria based on task type
        if "empathy" in rubric.criteria and len(action_history) > 0:
            criteria_scores["empathy"] = min(1.0, 0.4 + (reward_score * 0.6))
        
        if "validation" in rubric.criteria:
            criteria_scores["validation"] = 1.0 if "ask_details" in action_history else 0.5
        
        if "compliance_check" in rubric.criteria:
            criteria_scores["compliance_check"] = 0.9 if resolved else 0.4
        
        if "multi_issue_handling" in rubric.criteria:
            # Check if multiple actions taken
            action_set = set(action_history)
            criteria_scores["multi_issue_handling"] = 0.5 + (min(1.0, len(action_set) / 4.0) * 0.5)
        
        if "appropriate_response" in rubric.criteria:
            criteria_scores["appropriate_response"] = 0.75 + (reward_score * 0.25)
        
        if "follow_up" in rubric.criteria:
            # Best practices for follow-up
            has_followup = "reply" in action_history and len(action_history) > 3
            criteria_scores["follow_up"] = 1.0 if has_followup else 0.3
        
        # Calculate weighted score
        final_score = 0.0
        score_breakdown = {}
        
        for criterion, weight in rubric.criteria.items():
            criterion_score = criteria_scores.get(criterion, 0.0)
            score_breakdown[criterion] = {
                "score": round(criterion_score, 3),
                "weight": weight,
                "contribution": round(criterion_score * weight, 3)
            }
            final_score += criterion_score * weight
        
        # Ensure score is strictly between 0 and 1 (not 0.0 or 1.0)
        final_score = round(min(0.99, max(0.01, final_score)), 4)
        
        # Determine grade label
        if final_score >= rubric.threshold_excellent:
            label = "excellent"
        elif final_score >= rubric.threshold_good:
            label = "good"
        elif final_score >= rubric.threshold_acceptable:
            label = "acceptable"
        else:
            label = "needs_improvement"
        
        # Generate feedback
        feedback = self._generate_feedback(
            label,
            criteria_scores,
            action_history,
            step_count,
            max_steps,
            sentiment_trend
        )
        
        return {
            "raw_score": final_score,
            "final_score": final_score,
            "label": label,
            "breakdown": score_breakdown,
            "total_reward": round(total_reward, 4),
            "steps": step_count,
            "feedback": feedback,
            "detailed_metrics": {
                "efficiency": efficiency,
                "tone_handling": tone_score,
                "resolution_achieved": resolved,
                "actions_taken": len(set(action_history)),
                "reward_efficiency": round(total_reward / max(step_count, 1), 3)
            }
        }
    
    def _score_sequence(self, action_history: List[str], expected: List[str]) -> float:
        """Score how well the action sequence matches expected."""
        if not expected:
            return 1.0
        
        matched = self._count_sequence_match(action_history, expected)
        return round(matched / len(expected), 3)
    
    def _score_efficiency(self, actual_steps: int, max_steps: int) -> float:
        """Score efficiency based on step count."""
        if actual_steps == 0:
            return 1.0
        
        # Optimal is around 50% of max steps
        optimal = max_steps * 0.5
        
        if actual_steps <= optimal:
            return 1.0  # Perfect efficiency
        
        # Linearly decrease efficiency
        excess = actual_steps - optimal
        max_excess = max_steps - optimal
        penalty = (excess / max_excess) * 0.6
        
        return round(max(0.0, 1.0 - penalty), 3)
    
    def _score_tone_handling(self, tone: str, requires_handling: bool) -> float:
        """Score tone handling capability."""
        if not requires_handling:
            return 1.0  # Not required
        
        if tone == "angry":
            return 0.5  # Detected but challenging
        elif tone == "complaint":
            return 0.7  # Good identification
        else:
            return 1.0  # Neutral/positive
    
    def _count_sequence_match(self, action_history: List[str], expected: List[str]) -> int:
        """Count matching actions in order."""
        ei = 0
        for act in action_history:
            if ei < len(expected) and act == expected[ei]:
                ei += 1
        return ei
    
    def _generate_feedback(
        self,
        label: str,
        criteria_scores: Dict,
        actions: List[str],
        steps: int,
        max_steps: int,
        sentiment_trend: Optional[List[str]] = None
    ) -> Dict:
        """Generate detailed feedback for the user."""
        feedback = {
            "overall": "",
            "strengths": [],
            "improvements": [],
            "tips": []
        }
        
        # Overall message
        if label == "excellent":
            feedback["overall"] = "Outstanding performance! You handled this scenario exceptionally well."
        elif label == "good":
            feedback["overall"] = "Good work! You demonstrated solid customer support skills."
        elif label == "acceptable":
            feedback["overall"] = "Acceptable performance. With some practice, you can improve further."
        else:
            feedback["overall"] = "Room for improvement. Review the tips below to enhance your skills."
        
        # Identify strengths
        strong_criteria = [c for c, s in criteria_scores.items() if s >= 0.8]
        if strong_criteria:
            feedback["strengths"] = [f"Strong performance in {c.replace('_', ' ')}" for c in strong_criteria[:3]]
        
        # Identify improvements needed
        weak_criteria = [c for c, s in criteria_scores.items() if s < 0.5]
        if weak_criteria:
            feedback["improvements"] = [f"Focus on {c.replace('_', ' ')}" for c in weak_criteria[:3]]
        
        # Context-specific tips
        if steps > max_steps * 0.8:
            feedback["tips"].append("Try to resolve customer issues more efficiently with fewer steps.")
        
        if "ask_details" not in actions:
            feedback["tips"].append("Consider asking for more details to better understand customer needs.")
        
        if sentiment_trend and sentiment_trend[-1] == "angry" and sentiment_trend[0] != "angry":
            feedback["tips"].append("Good job de-escalating the situation!")
        
        return feedback


class BatchGrader:
    """Grade multiple sessions in batch with statistical analysis."""
    
    def __init__(self):
        self.advanced_grader = AdvancedGrader()
    
    def grade_batch(self, sessions: List[Dict]) -> Dict:
        """Grade multiple sessions and provide aggregate analysis."""
        if not sessions:
            return {"error": "No sessions provided"}
        
        grades = []
        
        for session in sessions:
            grade = self.advanced_grader.grade_comprehensive(
                task=session.get("task", {}),
                action_history=session.get("action_history", []),
                total_reward=session.get("total_reward", 0.0),
                final_state=session.get("final_state", ""),
                step_count=session.get("step_count", 0),
                intent_detected=session.get("intent_detected", ""),
                tone=session.get("tone", ""),
                conversation_history=session.get("conversation_history"),
                sentiment_trend=session.get("sentiment_trend")
            )
            grades.append(grade)
        
        # Calculate statistics
        scores = [g["final_score"] for g in grades]
        label_counts = {}
        for g in grades:
            label = g["label"]
            label_counts[label] = label_counts.get(label, 0) + 1
        
        import statistics
        
        return {
            "total_graded": len(grades),
            "grades": grades,
            "statistics": {
                "mean_score": round(statistics.mean(scores), 4),
                "median_score": round(statistics.median(scores), 4),
                "std_dev": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0,
                "min_score": round(min(scores), 4),
                "max_score": round(max(scores), 4)
            },
            "grade_distribution": label_counts,
            "pass_rate": round(
                len([g for g in grades if g["label"] in ("excellent", "good", "acceptable")]) / len(grades) * 100,
                2
            )
        }


# Global instances
grader = AdvancedGrader()
batch_grader = BatchGrader()
