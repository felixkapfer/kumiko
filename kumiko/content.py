from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adbs_legacy import load_content as load_adbs_content
from .catalog import Course, ExamRef


class ContentProviderError(ValueError):
    pass


def _load_json_content(course: Course, exam: ExamRef) -> dict[str, Any]:
    if not exam.content_path:
        raise ContentProviderError(
            f"Exam '{exam.id}' requires a contentPath."
        )
    path = (course.directory / exam.content_path).resolve()
    if course.directory.resolve() not in path.parents:
        raise ContentProviderError("contentPath leaves the course directory.")
    return json.loads(path.read_text(encoding="utf-8"))


def load_exam_content(course: Course, exam: ExamRef) -> dict[str, Any]:
    if exam.provider == "adbs-legacy":
        payload = load_adbs_content()
    elif exam.provider == "json-v1":
        payload = _load_json_content(course, exam)
    else:
        raise ContentProviderError(
            f"Unsupported content provider '{exam.provider}'."
        )

    return {
        **payload,
        "context": {
            "courseId": course.id,
            "examId": exam.id,
            "course": course.as_dict(),
            "exam": exam.as_dict(),
        },
    }
