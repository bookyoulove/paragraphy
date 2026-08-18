import json
import logging
import os
from pathlib import Path
from typing import Any

import frontmatter
from dotenv import load_dotenv
from sqlmodel import Session

from backend.orm.crud import CRUDProblem, CRUDRubric
from backend.orm.models import Problems
from backend.orm.session import create_db_and_table, db_engine
from backend.schema.problem import ProblemCreate, ProblemUpdate
from backend.schema.rubric import RubricCreate

logger = logging.getLogger(__name__)

load_dotenv()
problem_path = Path(os.getenv("PROBLEM_PATH", "problems"))


def _parse_md_file(file_path: Path) -> tuple[dict[str, Any], str] | None:
    try:
        post = frontmatter.load(file_path)
    except (OSError, ValueError, KeyError) as e:
        logger.warning(f"Failed to parse frontmatter from {file_path}: {e}")
        return None

    metadata = post.metadata
    if not isinstance(metadata, dict):
        return None

    required_keys = ("title", "university", "year", "type")
    if not all(k in metadata for k in required_keys):
        return None

    file_type = str(metadata.get("type", "")).strip().lower()
    if file_type not in ("problem", "solution"):
        return None

    title = str(metadata.get("title", "")).strip()
    university = str(metadata.get("university", "")).strip()
    try:
        year = int(metadata["year"])
    except ValueError, TypeError:
        return None

    if not title or not university:
        return None

    cleaned_metadata = {
        "title": title,
        "university": university,
        "year": year,
        "type": file_type,
    }
    return cleaned_metadata, post.content.strip()


def _load_rubrics(directory: Path) -> list[dict[str, Any]]:
    rubrics = []
    for json_file in sorted(directory.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "criteria" in item:
                        rubrics.append(
                            {
                                "criteria": str(item["criteria"]).strip(),
                                "description": (
                                    str(item["description"]).strip()
                                    if item.get("description") is not None
                                    else None
                                ),
                            }
                        )
            elif isinstance(data, dict) and "rubrics" in data:
                for item in data["rubrics"]:
                    if isinstance(item, dict) and "criteria" in item:
                        rubrics.append(
                            {
                                "criteria": str(item["criteria"]).strip(),
                                "description": (
                                    str(item["description"]).strip()
                                    if item.get("description") is not None
                                    else None
                                ),
                            }
                        )
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load rubric json from {json_file}: {e}")
    return rubrics


def load_problem(
    session: Session | None = None
) -> list[Problems]:
    directory = problem_path
    
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")


    # Group files by (directory, university, year, title)
    grouped: dict[tuple[Path, str, int, str], dict[str, Any]] = {}

    for next_file in sorted(directory.glob("**/*.md")):
        parsed = _parse_md_file(next_file)
        if parsed is None:
            continue

        metadata, content = parsed
        key = (
            next_file.parent,
            metadata["university"],
            metadata["year"],
            metadata["title"],
        )

        if key not in grouped:
            grouped[key] = {
                "parent_dir": next_file.parent,
                "university": metadata["university"],
                "year": metadata["year"],
                "title": metadata["title"],
                "problem_content": None,
                "solution_content": None,
            }

        if metadata["type"] == "problem":
            grouped[key]["problem_content"] = content
        elif metadata["type"] == "solution":
            grouped[key]["solution_content"] = content

    loaded_problems: list[Problems] = []

    def _process(db_session: Session):
        problem_db = CRUDProblem(db_session)
        rubric_db = CRUDRubric(db_session)

        for item in grouped.values():
            if not item["problem_content"]:
                continue

            title = item["title"]
            university = item["university"]
            year = item["year"]
            content = item["problem_content"]
            model_answer = item["solution_content"]
            parent_dir = item["parent_dir"]

            rubrics_data = _load_rubrics(parent_dir)

            existing_problem = problem_db.get_by_details(
                title=title,
                university=university,
                year=year,
                created_by_user=False,
            )

            if existing_problem is None:
                problem = problem_db.create(
                    ProblemCreate(
                        title=title,
                        content=content,
                        model_answer=model_answer,
                        created_by_user=False,
                        university=university,
                        year=year,
                        user_id=None,
                    )
                )
            else:
                problem = (
                    problem_db.update(
                        existing_problem.id,
                        ProblemUpdate(
                            title=title,
                            content=content,
                            model_answer=model_answer,
                        ),
                    )
                    or existing_problem
                )
                rubric_db.delete_by_problem(problem.id)

            rubric_objs = [
                RubricCreate(
                    problem_id=problem.id,
                    criteria=r_item["criteria"],
                    description=r_item["description"],
                )
                for r_item in rubrics_data
            ]
            rubric_db.create_multi(rubric_objs)

            loaded_problems.append(problem)

    if session is not None:
        _process(session)
    else:
        with Session(db_engine) as db_session:
            _process(db_session)

    return loaded_problems


if __name__ == "__main__":
    create_db_and_table()
    default_dir = Path(__file__).resolve().parents[4] / "essay_problems"
    print(f"Loading essay problems from: {default_dir}")
    problems = load_problem(default_dir)
    print(f"Successfully loaded {len(problems)} problem(s).")
