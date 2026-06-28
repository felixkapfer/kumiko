from __future__ import annotations

import json
import re
import sqlite3
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .catalog import (
    CatalogError,
    Course,
    catalog_payload,
    find_course,
    load_catalog,
)
from .config import Settings, load_settings
from .content import ContentProviderError, load_exam_content
from .state_schema import StateValidationError
from .storage import StateStore


MAX_REQUEST_BYTES = 25 * 1024 * 1024
CONTENT_ROUTE = re.compile(
    r"^/api/courses/(?P<course>[^/]+)/exams/(?P<exam>[^/]+)/content$"
)


class KumikoServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        settings: Settings,
        courses: tuple[Course, ...],
        store: StateStore,
    ) -> None:
        self.settings = settings
        self.courses = courses
        self.store = store
        super().__init__(address, KumikoHandler)


class KumikoHandler(SimpleHTTPRequestHandler):
    server: KumikoServer

    def translate_path(self, path: str) -> str:
        parsed_path = unquote(urlparse(path).path)
        relative = parsed_path.lstrip("/") or "index.html"
        candidate = (self.server.settings.project_root / relative).resolve()
        root = self.server.settings.project_root.resolve()
        if root not in candidate.parents and candidate != root:
            return str(root / "index.html")
        return str(candidate)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/catalog":
                self.send_json(catalog_payload(self.server.courses))
                return
            if parsed.path == "/api/state":
                self._get_state(parse_qs(parsed.query))
                return
            if parsed.path == "/api/content":
                course, exam_id = self._selected_course_and_exam()
                self.send_json(
                    load_exam_content(course, course.exam(exam_id))
                )
                return
            match = CONTENT_ROUTE.match(parsed.path)
            if match:
                course = find_course(
                    self.server.courses, unquote(match["course"])
                )
                exam = course.exam(unquote(match["exam"]))
                self.send_json(load_exam_content(course, exam))
                return
            if parsed.path == "/health":
                self.send_json(
                    {
                        "status": "ok",
                        "app": "Kumiko",
                        "courses": len(self.server.courses),
                        "database": str(
                            self.server.settings.database_path
                        ),
                    }
                )
                return
            super().do_GET()
        except (CatalogError, ContentProviderError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        if urlparse(self.path).path != "/api/state":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self.read_json()
            course = find_course(
                self.server.courses, payload.get("courseId", "")
            )
            course.exam(payload.get("examId", ""))
            self.send_json(self.server.store.save_state(payload))
        except (CatalogError, StateValidationError, ValueError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except sqlite3.Error as exc:
            self.send_json(
                {"error": f"Database error: {exc}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _get_state(self, query: dict[str, list[str]]) -> None:
        selected_course, selected_exam = (
            self.server.store.selected_context()
        )
        course_id = query.get("course", [selected_course])[0]
        course = find_course(self.server.courses, course_id or "")
        exam_id = query.get(
            "exam", [selected_exam or course.default_exam_id]
        )[0]
        course.exam(exam_id)
        self.send_json(self.server.store.load_state(course.id, exam_id))

    def _selected_course_and_exam(self) -> tuple[Course, str]:
        course_id, exam_id = self.server.store.selected_context()
        course = find_course(
            self.server.courses,
            course_id or self.server.courses[0].id,
        )
        return course, exam_id or course.default_exam_id

    def read_json(self) -> Any:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Request body is empty.")
        if content_length > MAX_REQUEST_BYTES:
            raise ValueError("Request body is too large.")
        return json.loads(self.rfile.read(content_length))

    def send_json(
        self, payload: Any, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        if self.path.startswith("/api/") or self.path == "/health":
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        print(f"[Kumiko] {self.address_string()} - {format % args}")


def build_server(settings: Settings | None = None) -> KumikoServer:
    settings = settings or load_settings()
    courses = load_catalog(settings.courses_dir)
    if not courses:
        raise RuntimeError(
            f"No courses found in {settings.courses_dir}."
        )
    default_course = courses[0]
    store = StateStore(
        settings.database_path,
        legacy_database_path=(
            settings.project_root / "data" / "adbs_exam_prep.sqlite3"
        ),
    )
    store.initialize(
        default_course.id, default_course.default_exam_id
    )
    return KumikoServer(
        (settings.host, settings.port), settings, courses, store
    )


def main() -> None:
    server = build_server()
    settings = server.settings
    print(f"Kumiko läuft auf http://{settings.host}:{settings.port}")
    print(f"Kurse: {len(server.courses)}")
    print(f"Persistente Datenbank: {settings.database_path}")
    print("Beenden mit Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
