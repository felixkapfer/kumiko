from __future__ import annotations

import json
from typing import Any


STATUS_VALUES = {"active", "archived", "deleted"}
MAX_EXAM_HISTORY = 25


class StateValidationError(ValueError):
    pass


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def validate_state(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise StateValidationError("State must be a JSON object.")

    course_id = _non_empty_string(payload, "courseId")
    exam_id = _non_empty_string(payload, "examId")
    language = payload.get("language", "de")
    if language not in {"de", "en"}:
        raise StateValidationError("language must be 'de' or 'en'.")

    progress = payload.get("progress", {})
    overrides = payload.get("questionOverrides", {})
    custom = payload.get("customQuestions", [])
    history = payload.get("examHistory", [])
    if not isinstance(progress, dict):
        raise StateValidationError("progress must be an object.")
    if not isinstance(overrides, dict):
        raise StateValidationError("questionOverrides must be an object.")
    if not isinstance(custom, list):
        raise StateValidationError("customQuestions must be an array.")
    if not isinstance(history, list):
        raise StateValidationError("examHistory must be an array.")

    _validate_overrides(overrides)
    _validate_custom_questions(custom)
    clean_history = _validate_history(history)

    return {
        "courseId": course_id,
        "examId": exam_id,
        "language": language,
        "progress": progress,
        "questionOverrides": overrides,
        "customQuestions": custom,
        "examHistory": clean_history,
    }


def _validate_overrides(overrides: dict[str, Any]) -> None:
    for question_id, override in overrides.items():
        if not isinstance(override, dict):
            raise StateValidationError(
                f"{question_id}: override must be an object."
            )
        if override.get("status", "active") not in STATUS_VALUES:
            raise StateValidationError(
                f"{question_id}: invalid question status."
            )


def _validate_custom_questions(custom: list[Any]) -> None:
    custom_ids: set[str] = set()
    for question in custom:
        if not isinstance(question, dict):
            raise StateValidationError(
                "Each custom question must be an object."
            )
        question_id = _non_empty_string(question, "id")
        if question_id in custom_ids:
            raise StateValidationError(
                f"Duplicate custom question id '{question_id}'."
            )
        custom_ids.add(question_id)
        options = question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise StateValidationError(
                f"{question_id}: at least two options are required."
            )


def _validate_history(history: list[Any]) -> list[dict[str, Any]]:
    clean_history: list[dict[str, Any]] = []
    history_ids: set[str] = set()
    for entry in history[:MAX_EXAM_HISTORY]:
        if (
            not isinstance(entry, dict)
            or not entry.get("id")
            or not isinstance(entry.get("questions"), list)
            or not isinstance(entry.get("answers"), dict)
            or not isinstance(entry.get("finishedAt"), int)
        ):
            raise StateValidationError("Invalid exam history entry.")
        if entry["id"] not in history_ids:
            history_ids.add(entry["id"])
            clean_history.append(entry)
    return clean_history


def _non_empty_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise StateValidationError(f"{key} must be a non-empty string.")
    return value.strip()
