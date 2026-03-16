from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite


class WorkflowRepository:
    def __init__(self, database_url: str) -> None:
        self._db_path = self._extract_sqlite_path(database_url)

    @staticmethod
    def _extract_sqlite_path(database_url: str) -> str:
        prefix = "sqlite+aiosqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite+aiosqlite URLs are currently supported")
        return database_url.removeprefix(prefix)

    async def initialize(self) -> None:
        db_path = Path(self._db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def save_workflow(
        self,
        workflow_id: str,
        goal: str,
        summary: str,
        plan: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO workflows (
                    workflow_id, goal, summary, plan_json, result_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    goal,
                    summary,
                    json.dumps(plan),
                    json.dumps(result),
                ),
            )
            await db.commit()

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT workflow_id, goal, summary, plan_json, result_json
                FROM workflows
                WHERE workflow_id = ?
                """,
                (workflow_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return {
            "workflow_id": row[0],
            "goal": row[1],
            "summary": row[2],
            "plan": json.loads(row[3]),
            "result": json.loads(row[4]),
        }
