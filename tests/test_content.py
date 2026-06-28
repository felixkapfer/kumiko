from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import server
from kumiko.storage import StateStore


ROOT = Path(__file__).resolve().parents[1]


class ContentTests(unittest.TestCase):
    def test_content_loader_accepts_all_bundled_files(self) -> None:
        payload = server.load_content()
        self.assertEqual(payload["errors"], [])
        self.assertEqual(len(payload["topics"]), 5)
        self.assertGreaterEqual(len(payload["glossary"]), 140)
        self.assertTrue(all(entry.get("tags") for entry in payload["glossary"]))
        self.assertTrue(all(entry.get("detail") for entry in payload["glossary"]))
        self.assertEqual(len(payload["questions"]), 250)
        self.assertGreaterEqual(
            len(payload["cypherExamples"]["examples"]), 60
        )
        self.assertEqual(len(payload["slides"]), 5)
        self.assertTrue(
            all(
                question.get("_languages") == ["de", "en"]
                for question in payload["questions"]
            )
        )

    def test_every_question_field_is_complete_in_german_and_english(self) -> None:
        for question in server.load_content()["questions"]:
            for field in ("prompt", "explanation"):
                self.assertTrue(question[field]["de"].strip(), question["id"])
                self.assertTrue(question[field]["en"].strip(), question["id"])
            if "context" in question:
                self.assertTrue(question["context"]["de"].strip(), question["id"])
                self.assertTrue(question["context"]["en"].strip(), question["id"])
            for option in question["options"]:
                for field in ("text", "explanation"):
                    self.assertTrue(option[field]["de"].strip(), question["id"])
                    self.assertTrue(option[field]["en"].strip(), question["id"])

    def test_question_ids_and_option_ids_are_unique(self) -> None:
        question_ids: set[str] = set()
        for path in sorted((ROOT / "content" / "questions").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for question in payload["questions"]:
                self.assertNotIn(question["id"], question_ids)
                question_ids.add(question["id"])
                option_ids = [option["id"] for option in question["options"]]
                self.assertEqual(len(option_ids), len(set(option_ids)))
                self.assertIn(question.get("_status", "active"), {"active", "archived", "deleted"})

        translations = json.loads(
            (ROOT / "content" / "questions.en.json").read_text(encoding="utf-8")
        )["translations"]
        self.assertEqual(set(translations), question_ids)

    def test_topics_and_difficulty_are_valid(self) -> None:
        payload = server.load_content()
        topics = {topic["id"] for topic in payload["topics"]}
        seen_difficulties: dict[str, set[int]] = {topic: set() for topic in topics}
        for question in payload["questions"]:
            self.assertIn(question["topic"], topics)
            self.assertIn(question["difficulty"], range(1, 6))
            seen_difficulties[question["topic"]].add(question["difficulty"])
        for levels in seen_difficulties.values():
            self.assertEqual(levels, {1, 2, 3, 4, 5})

    def test_pool_contains_all_and_none_correct_questions(self) -> None:
        questions = server.load_content()["questions"]
        correct_counts = [
            sum(option["correct"] for option in question["options"])
            for question in questions
        ]
        self.assertIn(0, correct_counts)
        self.assertTrue(
            any(
                count == len(question["options"])
                for count, question in zip(correct_counts, questions, strict=True)
            )
        )

    def test_glossary_details_are_substantive_and_not_generic(self) -> None:
        glossary = server.load_content()["glossary"]
        banned_phrases = {
            "ist ein prüfungsrelevanter begriff im themenblock",
            "in einer true-multiple-choice-frage kann",
            "achte darauf, den begriff nicht nur auswendig",
            "prüfe bei aussagen immer, ob sie absolut formuliert sind",
        }
        for entry in glossary:
            detail = entry["detail"]
            for language in ("de", "en"):
                self.assertGreaterEqual(
                    len(detail["keyPoints"][language]), 3, entry["term"]
                )
                self.assertGreaterEqual(
                    len(detail["details"][language]), 6, entry["term"]
                )
                self.assertGreaterEqual(
                    len(detail["examples"][language]), 1, entry["term"]
                )
                self.assertGreaterEqual(
                    len(detail["watchOut"][language]), 1, entry["term"]
                )
            self.assertGreaterEqual(len(detail["examQuestions"]), 1, entry["term"])
            self.assertTrue(detail.get("sourceSection"), entry["term"])
            serialized = json.dumps(detail, ensure_ascii=False).casefold()
            for phrase in banned_phrases:
                self.assertNotIn(phrase, serialized, entry["term"])

    def test_acid_detail_explains_all_properties_and_distinguishes_cap(self) -> None:
        glossary = server.load_content()["glossary"]
        acid = next(entry for entry in glossary if entry["term"] == "ACID")
        serialized = json.dumps(acid["detail"], ensure_ascii=False).casefold()
        for concept in (
            "atomicity",
            "consistency",
            "isolation",
            "durability",
            "banküberweisung",
            "cap-consistency",
        ):
            self.assertIn(concept, serialized)

    def test_every_glossary_term_has_beginner_text_and_exam_takeaway(self) -> None:
        glossary = server.load_content()["glossary"]
        self.assertEqual(
            {entry["term"] for entry in glossary},
            set(server.BEGINNER_EXPLANATIONS),
        )
        for entry in glossary:
            detail = entry["detail"]
            for language in ("de", "en"):
                simple = detail["simpleExplanation"][language]
                takeaway = detail["examTakeaway"][language]
                self.assertGreaterEqual(len(simple), 40, entry["term"])
                self.assertLessEqual(len(simple), 350, entry["term"])
                self.assertGreaterEqual(len(takeaway), 10, entry["term"])
                self.assertLessEqual(len(takeaway), 200, entry["term"])
                self.assertNotEqual(simple, takeaway, entry["term"])

    def test_glossary_sections_are_term_specific(self) -> None:
        glossary = server.load_content()["glossary"]
        for field in ("details", "examples", "watchOut"):
            values = [
                tuple(entry["detail"][field]["de"])
                for entry in glossary
            ]
            self.assertEqual(len(values), len(set(values)), field)
        aggregate = next(entry for entry in glossary if entry["term"] == "Aggregate")
        aggregate_text = json.dumps(
            aggregate["detail"], ensure_ascii=False
        ).casefold()
        self.assertIn("bestellung", aggregate_text)
        self.assertIn("aggregatgrenze", aggregate_text)

    def test_every_answer_explanation_teaches_the_actual_concept(self) -> None:
        payload = server.load_content()
        banned = (
            "dieser begriff bezeichnet ein anderes konzept",
            "this term denotes a different concept",
            "diese definition gehört zu diesem begriff",
            "this definition belongs to this term",
        )
        for question in payload["questions"]:
            for option in question["options"]:
                explanation = option.get("explanation", "")
                if isinstance(explanation, dict):
                    explanation = explanation.get("de", "")
                self.assertGreaterEqual(len(explanation.strip()), 8, question["id"])
                folded = explanation.casefold()
                for phrase in banned:
                    self.assertNotIn(phrase, folded, question["id"])

            if question.get("_generated") and question["id"].startswith(
                "glossary-term-"
            ):
                for option in question["options"]:
                    term = option["text"]["de"]
                    explanation = option["explanation"]["de"]
                    self.assertIn(term.casefold(), explanation.casefold())
                    matching = next(
                        entry
                        for entry in payload["glossary"]
                        if entry["term"] == term
                    )
                    self.assertIn(
                        matching["definition"].casefold(),
                        explanation.casefold(),
                    )

    def test_every_study_chapter_has_concepts_and_questions(self) -> None:
        payload = server.load_content()
        glossary_terms = {entry["term"] for entry in payload["glossary"]}
        question_ids = {question["id"] for question in payload["questions"]}
        for topic in payload["topics"]:
            for section in topic["sections"]:
                self.assertGreaterEqual(len(section["studyTerms"]), 5)
                self.assertGreaterEqual(len(section["questionIds"]), 3)
                self.assertTrue(set(section["studyTerms"]).issubset(glossary_terms))
                self.assertTrue(
                    set(section["questionIds"]).issubset(question_ids)
                )

    def test_cypher_examples_cover_all_difficulty_levels(self) -> None:
        material = server.load_content()["cypherExamples"]
        examples = material["examples"]
        self.assertEqual(material["version"], 1)
        self.assertTrue(material["setup"]["query"])
        self.assertTrue(material["matchVsWhere"]["takeaway"]["de"])
        self.assertEqual(len({example["id"] for example in examples}), len(examples))
        self.assertEqual(
            {example["difficulty"] for example in examples},
            {1, 2, 3, 4, 5},
        )
        self.assertGreaterEqual(
            sum(
                example.get("scope") == "supplemental"
                for example in examples
            ),
            10,
        )
        for example in examples:
            self.assertIn(example["difficulty"], range(1, 6))
            self.assertTrue(example["category"])
            for field in ("title", "question", "explanation", "expectedResult"):
                self.assertTrue(example[field]["de"], example["id"])
                self.assertTrue(example[field]["en"], example["id"])
            self.assertGreaterEqual(len(example["query"].strip()), 15)

    def test_sqlite_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.sqlite3"
            payload = {
                "version": 2,
                "courseId": "adbs",
                "examId": "practical-test-3-2026",
                "language": "en",
                "progress": {
                    "q-1": {
                        "attempts": 2,
                        "correct": 1,
                        "lastResult": False,
                    }
                },
                "questionOverrides": {
                    "q-1": {
                        "status": "archived",
                        "changedAt": 123,
                    }
                },
                "customQuestions": [
                    {
                        "id": "custom-db-test",
                        "topic": "nosql",
                        "difficulty": 2,
                        "status": "active",
                        "prompt": "Test?",
                        "options": [
                            {
                                "id": "a",
                                "text": "Yes",
                                "correct": True,
                            },
                            {
                                "id": "b",
                                "text": "No",
                                "correct": False,
                            },
                        ],
                    }
                ],
                "examHistory": [
                    {
                        "id": "exam-1",
                        "finishedAt": 456,
                        "questions": [],
                        "answers": {},
                    }
                ],
            }

            store = StateStore(database)
            store.initialize("adbs", "practical-test-3-2026")
            saved = store.save_state(payload)
            loaded = store.load_state("adbs", "practical-test-3-2026")

            self.assertTrue(saved["hasData"])
            self.assertEqual(loaded["language"], "en")
            self.assertEqual(loaded["progress"], payload["progress"])
            self.assertEqual(
                loaded["questionOverrides"], payload["questionOverrides"]
            )
            self.assertEqual(
                loaded["customQuestions"][0]["id"], "custom-db-test"
            )
            self.assertEqual(loaded["examHistory"][0]["id"], "exam-1")


if __name__ == "__main__":
    unittest.main()
