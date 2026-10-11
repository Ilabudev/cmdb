"""Обход графа связей рекурсивным CTE.

Связь source → target означает «source зависит от target».
downstream — то, от чего зависит CI (идём по source → target);
upstream   — то, что зависит от CI (идём по target → source), т.е. анализ влияния.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import Direction, Graph, GraphEdge, GraphNode

_WALK = """
WITH RECURSIVE walk(ci_id, depth, path) AS (
    SELECT CAST(:root AS uuid), 0, ARRAY[CAST(:root AS uuid)]
  UNION ALL
    SELECT nxt.id, w.depth + 1, w.path || nxt.id
    FROM walk w
    JOIN relations r ON r.deleted_at IS NULL AND ({join})
    JOIN relation_types rt ON rt.id = r.type_id AND (NOT :impact_only OR rt.propagates_impact)
    CROSS JOIN LATERAL (SELECT {next_expr} AS id) nxt
    WHERE w.depth < :depth AND NOT nxt.id = ANY(w.path)
)
SELECT ci_id, MIN(depth) AS depth FROM walk GROUP BY ci_id
"""

_DIRECTIONS = {
    "downstream": ("r.source_id = w.ci_id", "r.target_id"),
    "upstream": ("r.target_id = w.ci_id", "r.source_id"),
    "both": (
        "w.ci_id IN (r.source_id, r.target_id)",
        "CASE WHEN r.source_id = w.ci_id THEN r.target_id ELSE r.source_id END",
    ),
}


async def neighbourhood(
    session: AsyncSession,
    root: uuid.UUID,
    *,
    depth: int = 2,
    direction: Direction = "both",
    impact_only: bool = False,
) -> Graph:
    join, next_expr = _DIRECTIONS[direction]
    reached = (
        await session.execute(
            text(_WALK.format(join=join, next_expr=next_expr)),
            {"root": root, "depth": depth, "impact_only": impact_only},
        )
    ).all()
    depths = {row.ci_id: row.depth for row in reached}
    if not depths:
        return Graph(nodes=[], edges=[])

    nodes = (
        await session.execute(
            text(
                "SELECT c.id, c.name, c.status, t.code AS type_code FROM cis c "
                "JOIN ci_types t ON t.id = c.type_id "
                "WHERE c.id = ANY(:ids) AND c.deleted_at IS NULL"
            ),
            {"ids": list(depths)},
        )
    ).all()
    edges = (
        await session.execute(
            text(
                "SELECT r.id, r.source_id, r.target_id, rt.code AS type_code FROM relations r "
                "JOIN relation_types rt ON rt.id = r.type_id "
                "WHERE r.deleted_at IS NULL "
                "AND r.source_id = ANY(:ids) AND r.target_id = ANY(:ids)"
            ),
            {"ids": list(depths)},
        )
    ).all()
    return Graph(
        nodes=[
            GraphNode(id=n.id, name=n.name, type_code=n.type_code, status=n.status, depth=depths[n.id])
            for n in nodes
        ],
        edges=[
            GraphEdge(id=e.id, type_code=e.type_code, source_id=e.source_id, target_id=e.target_id)
            for e in edges
        ],
    )
