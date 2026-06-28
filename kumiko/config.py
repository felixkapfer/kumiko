from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    project_root: Path
    courses_dir: Path
    data_dir: Path
    database_path: Path


def load_settings() -> Settings:
    data_dir = Path(
        os.environ.get("KUMIKO_DATA_DIR", PROJECT_ROOT / "data")
    ).resolve()
    courses_dir = Path(
        os.environ.get("KUMIKO_COURSES_DIR", PROJECT_ROOT / "courses")
    ).resolve()
    database_name = os.environ.get(
        "KUMIKO_DATABASE_NAME", "kumiko.sqlite3"
    )
    return Settings(
        host=os.environ.get("KUMIKO_HOST", "127.0.0.1"),
        port=int(os.environ.get("KUMIKO_PORT", "8000")),
        project_root=PROJECT_ROOT,
        courses_dir=courses_dir,
        data_dir=data_dir,
        database_path=data_dir / database_name,
    )
