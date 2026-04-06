from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from support_inbox_env.graders import evaluate_progress
from support_inbox_env.models import (
    ActionRecord,
    ActionType,
    EnvironmentState,
    ProgressChecklist,
    StepResponse,
    SupportAction,
    SupportObservation,
    SupportReward,
    TaskSpec,
)
from support_inbox_env.tasks import TASK_LOOKUP, TASKS


@dataclass
class EpisodeMemory:
    task: TaskSpec
    step_index: int = 0
    done: bool = False
    latest_values: Dict[ActionType, SupportAction] = field(default_factory=dict)
    history: List[ActionRecord] = field(default_factory=list)
    cumulative_score: float = 0.0
    current_score: float = 0.0


class SupportInboxEnvironment:
    def __init__(self) -> None:
        self._task_order = [task.task_id for task in TASKS]
        self._task_cursor = 0
        self._episode: Optional[EpisodeMemory] = None

    def list_tasks(self) -> list[dict]:
        return [
            {
                "task_id": task.task_id,
                "title": task.title,
                "difficulty": task.difficulty.value,
                "description": task.description,
            }
            for task in TASKS
        ]

    def reset(self, task_id: Optional[str] = None) -> SupportObservation:
        chosen_task_id = task_id or self._task_order[self._task_cursor % len(self._task_order)]
        self._task_cursor += 1
        task = TASK_LOOKUP[chosen_task_id]
        self._episode = EpisodeMemory(task=task)
        return self._build_observation("Environment reset. Review the ticket and begin triage.")

    def step(self, action: SupportAction) -> StepResponse:
        if self._episode is None:
            self.reset()
        assert self._episode is not None

        if self._episode.done:
            observation = self._build_observation("Episode is already finished. Call reset() for a new task.")
            return StepResponse(
                observation=observation,
                reward=SupportReward(value=0.0, components={}, reasoning="No-op after episode completion."),
                done=True,
                info={"grader_score": self._episode.current_score},
            )

        self._episode.step_index += 1
        self._episode.latest_values[action.action_type] = action
        self._episode.history.append(
            ActionRecord(
                step_index=self._episode.step_index,
                action_type=action.action_type,
                value=action.value,
                message=action.message,
            )
        )

        components, new_score = evaluate_progress(self._episode.task, self._episode.latest_values)
        incremental = max(0.0, round(new_score - self._episode.current_score, 4))

        repeated_penalty = 0.0
        if sum(1 for item in self._episode.history if item.action_type == action.action_type) > 1:
            repeated_penalty = 0.05

        step_reward_value = max(0.0, round(incremental - repeated_penalty, 4))
        self._episode.current_score = new_score
        self._episode.cumulative_score = min(1.0, round(self._episode.cumulative_score + step_reward_value, 4))

        final_action_taken = action.action_type in {ActionType.RESOLVE, ActionType.ESCALATE}
        turn_limit_reached = self._episode.step_index >= self._episode.task.max_turns
        self._episode.done = final_action_taken or turn_limit_reached or new_score >= 0.999

        reasoning = self._build_reasoning(action, incremental, repeated_penalty, final_action_taken, turn_limit_reached)
        observation = self._build_observation(reasoning)

        return StepResponse(
            observation=observation,
            reward=SupportReward(
                value=step_reward_value,
                components=components,
                reasoning=reasoning,
            ),
            done=self._episode.done,
            info={
                "grader_score": new_score,
                "cumulative_score": self._episode.cumulative_score,
                "task_id": self._episode.task.task_id,
            },
        )

    def state(self) -> EnvironmentState:
        if self._episode is None:
            return EnvironmentState()
        return EnvironmentState(
            active_task_id=self._episode.task.task_id,
            observation=self._build_observation("Current environment state."),
            done=self._episode.done,
            cumulative_score=self._episode.cumulative_score,
            grader_score=self._episode.current_score,
        )

    def _build_reasoning(
        self,
        action: SupportAction,
        incremental: float,
        repeated_penalty: float,
        final_action_taken: bool,
        turn_limit_reached: bool,
    ) -> str:
        notes = [f"Processed `{action.action_type.value}`."]
        if incremental > 0:
            notes.append(f"Progress improved by {incremental:.2f}.")
        if repeated_penalty > 0:
            notes.append("Repeated action type reduced the incremental reward.")
        if final_action_taken:
            notes.append("A final disposition was taken, so the episode is complete.")
        if turn_limit_reached:
            notes.append("Turn limit reached.")
        if len(notes) == 1:
            notes.append("No additional rubric progress was earned on this step.")
        return " ".join(notes)

    def _build_observation(self, guidance: str) -> SupportObservation:
        assert self._episode is not None
        task = self._episode.task
        checklist = ProgressChecklist(
            intent_done=self._matches(ActionType.CLASSIFY_INTENT, task.expected_intent),
            priority_done=self._matches(ActionType.SET_PRIORITY, task.expected_priority),
            team_done=self._matches(ActionType.ASSIGN_TEAM, task.expected_team),
            reply_done=self._reply_complete(),
            final_action_done=self._final_action_complete(),
        )

        return SupportObservation(
            task_id=task.task_id,
            title=task.title,
            difficulty=task.difficulty,
            objective=task.description,
            ticket=task.ticket,
            checklist=checklist,
            action_history=list(self._episode.history),
            current_status="done" if self._episode.done else "in_progress",
            remaining_turns=max(0, task.max_turns - self._episode.step_index),
            available_actions=[
                ActionType.CLASSIFY_INTENT,
                ActionType.SET_PRIORITY,
                ActionType.ASSIGN_TEAM,
                ActionType.DRAFT_REPLY,
                ActionType.RESOLVE,
                ActionType.ESCALATE,
            ],
            guidance=guidance,
        )

    def _matches(self, action_type: ActionType, expected: str) -> bool:
        assert self._episode is not None
        action = self._episode.latest_values.get(action_type)
        return bool(action and action.value == expected)

    def _reply_complete(self) -> bool:
        assert self._episode is not None
        draft = self._episode.latest_values.get(ActionType.DRAFT_REPLY)
        if not draft:
            return False
        text = draft.message.lower()
        return all(keyword.lower() in text for keyword in self._episode.task.required_reply_keywords)

    def _final_action_complete(self) -> bool:
        assert self._episode is not None
        task = self._episode.task
        if task.final_action == "resolve":
            action = self._episode.latest_values.get(ActionType.RESOLVE)
            return bool(action and action.value == task.resolution_value)

        action = self._episode.latest_values.get(ActionType.ESCALATE)
        if not action or action.value != task.resolution_value:
            return False
        note = action.message.lower()
        return all(keyword.lower() in note for keyword in task.escalation_note_keywords)
