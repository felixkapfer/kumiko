from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class ExamRef:
    id: str
    title: str
    date: str | None
    provider: str
    content_path: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "provider": self.provider,
        }


@dataclass(frozen=True)
class Course:
    id: str
    code: str
    title: str
    university: str
    degree: str
    semester: str
    description: str
    color: str
    status: str
    default_exam_id: str
    exams: tuple[ExamRef, ...]
    directory: Path

    def exam(self, exam_id: str) -> ExamRef:
        for exam in self.exams:
            if exam.id == exam_id:
                return exam
        raise CatalogError(
            f"Unknown exam '{exam_id}' for course '{self.id}'."
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "university": self.university,
            "degree": self.degree,
            "semester": self.semester,
            "description": self.description,
            "color": self.color,
            "status": self.status,
            "defaultExamId": self.default_exam_id,
            "exams": [exam.as_dict() for exam in self.exams],
        }


def _required_string(payload: dict[str, Any], key: str, source: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{source}: '{key}' must be a non-empty string.")
    return value.strip()


def load_course(path: Path) -> Course:
    source = path / "course.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("version") != 1:
        raise CatalogError(f"{source}: version must be 1.")

    exams_payload = payload.get("exams")
    if not isinstance(exams_payload, list) or not exams_payload:
        raise CatalogError(f"{source}: at least one exam is required.")

    exams: list[ExamRef] = []
    exam_ids: set[str] = set()
    for item in exams_payload:
        if not isinstance(item, dict):
            raise CatalogError(f"{source}: each exam must be an object.")
        exam_id = _required_string(item, "id", source)
        if exam_id in exam_ids:
            raise CatalogError(f"{source}: duplicate exam id '{exam_id}'.")
        exam_ids.add(exam_id)
        exams.append(
            ExamRef(
                id=exam_id,
                title=_required_string(item, "title", source),
                date=item.get("date"),
                provider=_required_string(item, "provider", source),
                content_path=item.get("contentPath"),
            )
        )

    default_exam_id = payload.get("defaultExamId", exams[0].id)
    if default_exam_id not in exam_ids:
        raise CatalogError(
            f"{source}: defaultExamId '{default_exam_id}' does not exist."
        )

    return Course(
        id=_required_string(payload, "id", source),
        code=_required_string(payload, "code", source),
        title=_required_string(payload, "title", source),
        university=_required_string(payload, "university", source),
        degree=_required_string(payload, "degree", source),
        semester=_required_string(payload, "semester", source),
        description=_required_string(payload, "description", source),
        color=payload.get("color", "#b8f34a"),
        status=payload.get("status", "active"),
        default_exam_id=default_exam_id,
        exams=tuple(exams),
        directory=path,
    )


def load_catalog(courses_dir: Path) -> tuple[Course, ...]:
    if not courses_dir.exists():
        return ()
    courses = tuple(
        load_course(path)
        for path in sorted(courses_dir.iterdir())
        if path.is_dir() and (path / "course.json").exists()
    )
    ids = [course.id for course in courses]
    if len(ids) != len(set(ids)):
        raise CatalogError("Course ids must be globally unique.")
    return courses


def find_course(courses: tuple[Course, ...], course_id: str) -> Course:
    for course in courses:
        if course.id == course_id:
            return course
    raise CatalogError(f"Unknown course '{course_id}'.")


def catalog_payload(courses: tuple[Course, ...]) -> dict[str, Any]:
    return {
        "version": 1,
        "app": {
            "name": "Kumiko",
            "repository": "kumiko-study",
        },
        "courses": [course.as_dict() for course in courses],
    }
