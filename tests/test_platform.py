from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kumiko.catalog import catalog_payload, load_catalog
from kumiko.content import load_exam_content
from kumiko.storage import StateStore


ROOT = Path(__file__).resolve().parents[1]


class PlatformTests(unittest.TestCase):
    def test_catalog_discovers_courses_and_exams(self) -> None:
        courses = load_catalog(ROOT / "courses")
        self.assertEqual([course.id for course in courses], ["adbs", "air"])
        course = courses[0]
        self.assertEqual(course.default_exam_id, "practical-test-3-2026")
        self.assertEqual(
            course.exam(course.default_exam_id).provider, "adbs-legacy"
        )
        air = courses[1]
        self.assertEqual(air.default_exam_id, "final-2026")
        self.assertEqual(air.exam(air.default_exam_id).provider, "json-v1")
        payload = catalog_payload(courses)
        self.assertEqual(payload["app"]["name"], "Kumiko")

    def test_air_content_loads_signed_selection_scoring(self) -> None:
        courses = load_catalog(ROOT / "courses")
        air = next(course for course in courses if course.id == "air")
        payload = load_exam_content(air, air.exam("final-2026"))
        self.assertEqual(payload["context"]["courseId"], "air")
        self.assertEqual(payload["scoring"]["type"], "signed-selection")
        self.assertGreaterEqual(len(payload["questions"]), 30)
        self.assertTrue(
            all(len(question["options"]) >= 4 for question in payload["questions"])
        )

    def test_json_provider_loads_generic_exam_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            course_dir = Path(directory) / "sample"
            content_dir = course_dir / "exams" / "final"
            content_dir.mkdir(parents=True)
            content = {
                "topics": [],
                "glossary": [],
                "questions": [],
                "sources": [],
                "slides": [],
                "errors": [],
            }
            (content_dir / "content.json").write_text(
                json.dumps(content), encoding="utf-8"
            )
            (course_dir / "course.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "id": "sample",
                        "code": "SAMPLE",
                        "title": "Sample Course",
                        "university": "TU Wien",
                        "degree": "Masterstudium",
                        "semester": "2026",
                        "description": "Test course",
                        "defaultExamId": "final",
                        "exams": [
                            {
                                "id": "final",
                                "title": "Final",
                                "provider": "json-v1",
                                "contentPath": "exams/final/content.json",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            course = load_catalog(Path(directory))[0]
            payload = load_exam_content(course, course.exam("final"))
            self.assertEqual(payload["context"]["courseId"], "sample")
            self.assertEqual(payload["questions"], [])

    def test_state_is_isolated_by_course_and_exam(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "kumiko.sqlite3")
            store.initialize("course-a", "exam-a")
            base = {
                "version": 2,
                "language": "de",
                "questionOverrides": {},
                "customQuestions": [],
                "examHistory": [],
            }
            store.save_state(
                {
                    **base,
                    "courseId": "course-a",
                    "examId": "exam-a",
                    "progress": {"q1": {"attempts": 1}},
                }
            )
            store.save_state(
                {
                    **base,
                    "courseId": "course-a",
                    "examId": "exam-b",
                    "progress": {"q1": {"attempts": 9}},
                }
            )
            self.assertEqual(
                store.load_state("course-a", "exam-a")["progress"]["q1"][
                    "attempts"
                ],
                1,
            )
            self.assertEqual(
                store.load_state("course-a", "exam-b")["progress"]["q1"][
                    "attempts"
                ],
                9,
            )


if __name__ == "__main__":
    unittest.main()
