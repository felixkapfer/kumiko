from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .state_schema import (
    MAX_EXAM_HISTORY,
    encode_json,
    validate_state,
)


class StateStore:
    def __init__(
        self,
        database_path: Path,
        *,
        legacy_database_path: Path | None = None,
    ) -> None:
        self.database_path = database_path
        self.legacy_database_path = legacy_database_path

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(
        self, default_course_id: str, default_exam_id: str
    ) -> None:
        connection = self.connect()
        try:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS progress (
                        course_id TEXT NOT NULL,
                        exam_id TEXT NOT NULL,
                        question_id TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        PRIMARY KEY(course_id, exam_id, question_id)
                    );

                    CREATE TABLE IF NOT EXISTS question_overrides (
                        course_id TEXT NOT NULL,
                        exam_id TEXT NOT NULL,
                        question_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        changed_at INTEGER,
                        payload TEXT NOT NULL,
                        PRIMARY KEY(course_id, exam_id, question_id)
                    );

                    CREATE TABLE IF NOT EXISTS custom_questions (
                        course_id TEXT NOT NULL,
                        exam_id TEXT NOT NULL,
                        question_id TEXT NOT NULL,
                        imported_at INTEGER NOT NULL,
                        payload TEXT NOT NULL,
                        PRIMARY KEY(course_id, exam_id, question_id)
                    );

                    CREATE TABLE IF NOT EXISTS exam_history (
                        course_id TEXT NOT NULL,
                        exam_id TEXT NOT NULL,
                        history_id TEXT NOT NULL,
                        finished_at INTEGER NOT NULL,
                        payload TEXT NOT NULL,
                        PRIMARY KEY(course_id, exam_id, history_id)
                    );
                    """
                )
                self._set_default(
                    connection, "selectedCourseId", default_course_id
                )
                self._set_default(
                    connection, "selectedExamId", default_exam_id
                )
                self._set_default(connection, "language", "de")
        finally:
            connection.close()

        self._migrate_legacy_state(default_course_id, default_exam_id)

    @staticmethod
    def _set_default(
        connection: sqlite3.Connection, key: str, value: str
    ) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            (key, value),
        )

    def selected_context(self) -> tuple[str | None, str | None]:
        connection = self.connect()
        try:
            values = {
                row["key"]: row["value"]
                for row in connection.execute(
                    """
                    SELECT key, value
                    FROM settings
                    WHERE key IN ('selectedCourseId', 'selectedExamId')
                    """
                )
            }
        finally:
            connection.close()
        return values.get("selectedCourseId"), values.get("selectedExamId")

    def load_state(self, course_id: str, exam_id: str) -> dict[str, Any]:
        connection = self.connect()
        try:
            settings = {
                row["key"]: row["value"]
                for row in connection.execute(
                    "SELECT key, value FROM settings"
                )
            }
            progress = self._object_rows(
                connection,
                "progress",
                course_id,
                exam_id,
                "question_id",
            )
            overrides = self._object_rows(
                connection,
                "question_overrides",
                course_id,
                exam_id,
                "question_id",
            )
            custom = [
                json.loads(row["payload"])
                for row in connection.execute(
                    """
                    SELECT payload
                    FROM custom_questions
                    WHERE course_id = ? AND exam_id = ?
                    ORDER BY imported_at, question_id
                    """,
                    (course_id, exam_id),
                )
            ]
            history = [
                json.loads(row["payload"])
                for row in connection.execute(
                    """
                    SELECT payload
                    FROM exam_history
                    WHERE course_id = ? AND exam_id = ?
                    ORDER BY finished_at DESC, history_id DESC
                    LIMIT ?
                    """,
                    (course_id, exam_id, MAX_EXAM_HISTORY),
                )
            ]
        finally:
            connection.close()

        return {
            "version": 2,
            "hasData": bool(progress or overrides or custom or history),
            "courseId": course_id,
            "examId": exam_id,
            "language": settings.get("language", "de"),
            "progress": progress,
            "questionOverrides": overrides,
            "customQuestions": custom,
            "examHistory": history,
        }

    @staticmethod
    def _object_rows(
        connection: sqlite3.Connection,
        table: str,
        course_id: str,
        exam_id: str,
        key_column: str,
    ) -> dict[str, Any]:
        rows = connection.execute(
            f"""
            SELECT {key_column}, payload
            FROM {table}
            WHERE course_id = ? AND exam_id = ?
            ORDER BY {key_column}
            """,
            (course_id, exam_id),
        )
        return {
            row[key_column]: json.loads(row["payload"]) for row in rows
        }

    def save_state(self, payload: Any) -> dict[str, Any]:
        state = validate_state(payload)
        course_id = state["courseId"]
        exam_id = state["examId"]
        connection = self.connect()
        try:
            with connection:
                for table in (
                    "progress",
                    "question_overrides",
                    "custom_questions",
                    "exam_history",
                ):
                    connection.execute(
                        f"DELETE FROM {table} "
                        "WHERE course_id = ? AND exam_id = ?",
                        (course_id, exam_id),
                    )

                connection.executemany(
                    """
                    INSERT INTO progress(
                        course_id, exam_id, question_id, payload
                    ) VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            course_id,
                            exam_id,
                            question_id,
                            encode_json(value),
                        )
                        for question_id, value in state["progress"].items()
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO question_overrides(
                        course_id, exam_id, question_id,
                        status, changed_at, payload
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            course_id,
                            exam_id,
                            question_id,
                            value.get("status", "active"),
                            value.get("changedAt"),
                            encode_json(value),
                        )
                        for question_id, value in state[
                            "questionOverrides"
                        ].items()
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO custom_questions(
                        course_id, exam_id, question_id,
                        imported_at, payload
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            course_id,
                            exam_id,
                            question["id"],
                            int(question.get("_importedAt", index)),
                            encode_json(question),
                        )
                        for index, question in enumerate(
                            state["customQuestions"]
                        )
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO exam_history(
                        course_id, exam_id, history_id,
                        finished_at, payload
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            course_id,
                            exam_id,
                            entry["id"],
                            entry["finishedAt"],
                            encode_json(entry),
                        )
                        for entry in state["examHistory"]
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO settings(key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (
                        ("language", state["language"]),
                        ("selectedCourseId", course_id),
                        ("selectedExamId", exam_id),
                    ),
                )
        finally:
            connection.close()
        return self.load_state(course_id, exam_id)

    def _migrate_legacy_state(
        self, default_course_id: str, default_exam_id: str
    ) -> None:
        legacy_path = self.legacy_database_path
        if (
            legacy_path is None
            or legacy_path == self.database_path
            or not legacy_path.exists()
            or self.load_state(default_course_id, default_exam_id)["hasData"]
        ):
            return

        legacy = sqlite3.connect(legacy_path)
        legacy.row_factory = sqlite3.Row
        try:
            tables = {
                row["name"]
                for row in legacy.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            required = {
                "settings",
                "progress",
                "question_overrides",
                "custom_questions",
                "exam_history",
            }
            if not required.issubset(tables):
                return
            settings = {
                row["key"]: row["value"]
                for row in legacy.execute("SELECT key, value FROM settings")
            }
            payload = {
                "version": 2,
                "courseId": default_course_id,
                "examId": default_exam_id,
                "language": settings.get("language", "de"),
                "progress": {
                    row["question_id"]: json.loads(row["payload"])
                    for row in legacy.execute(
                        "SELECT question_id, payload FROM progress"
                    )
                },
                "questionOverrides": {
                    row["question_id"]: json.loads(row["payload"])
                    for row in legacy.execute(
                        """
                        SELECT question_id, payload
                        FROM question_overrides
                        """
                    )
                },
                "customQuestions": [
                    json.loads(row["payload"])
                    for row in legacy.execute(
                        """
                        SELECT payload FROM custom_questions
                        ORDER BY imported_at, question_id
                        """
                    )
                ],
                "examHistory": [
                    json.loads(row["payload"])
                    for row in legacy.execute(
                        """
                        SELECT payload FROM exam_history
                        ORDER BY finished_at DESC, exam_id DESC
                        LIMIT ?
                        """,
                        (MAX_EXAM_HISTORY,),
                    )
                ],
            }
        except sqlite3.Error:
            return
        finally:
            legacy.close()
        self.save_state(payload)
