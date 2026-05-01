"""Audit + finding routes.

POST /api/audits/{name}             → AuditReport             (run single)
POST /api/audits/run-all            → AuditAggregate          (run all + persist)
GET  /api/findings?status=open      → list[Finding]
POST /api/findings/{id}/dismiss     → {ok: True}
POST /api/findings/{id}/apply-fix   → {ok, message}            (Phase 7 wires real fixes)
"""
from __future__ import annotations

import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.audits import REGISTRY
from app.auth import User, get_current_user
from app.db import db
from app.schemas import AuditAggregate, AuditReport, Finding, FindingStatus

router = APIRouter(prefix="/api", tags=["audits"])

_VALID_STATUSES: frozenset[str] = frozenset({"open", "fixed", "dismissed"})


async def _persist_finding(f: Finding, now: float) -> None:
    """INSERT OR REPLACE the finding by id. created_at preserved when present;
    updated_at always bumped. Status defaults to 'open' if blank."""
    created_at = f.created_at if f.created_at is not None else now
    await db.execute(
        """
        INSERT INTO findings (id, category, severity, title, description, evidence, fix_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            category=excluded.category,
            severity=excluded.severity,
            title=excluded.title,
            description=excluded.description,
            evidence=excluded.evidence,
            fix_id=excluded.fix_id,
            updated_at=excluded.updated_at
        """,
        (
            f.id,
            f.category,
            f.severity,
            f.title,
            f.description,
            json.dumps(f.evidence, default=str),
            f.fix_id,
            f.status or "open",
            created_at,
            now,
        ),
    )


def _row_to_finding(row: tuple) -> Finding:
    """Map a findings-table row tuple to a Finding model."""
    fid, category, severity, title, description, evidence, fix_id, status_, created_at, _updated = row
    try:
        evidence_obj = json.loads(evidence) if evidence else {}
        if not isinstance(evidence_obj, dict):
            evidence_obj = {"value": evidence_obj}
    except (TypeError, ValueError):
        evidence_obj = {}
    return Finding(
        id=fid,
        category=category,
        severity=severity,
        title=title,
        description=description,
        evidence=evidence_obj,
        fix_id=fix_id,
        status=status_,
        created_at=created_at,
    )


@router.post("/audits/run-all", response_model=AuditAggregate)
async def run_all_audits(
    _user: Annotated[User, Depends(get_current_user)],
) -> AuditAggregate:
    """Run every registered audit and upsert each finding into the DB."""
    reports: list[AuditReport] = []
    total = 0
    now = time.time()
    for name, fn in REGISTRY.items():
        try:
            report = await fn()
        except Exception as e:  # never let one audit kill the aggregate
            report = AuditReport(name=name, findings=[])
            # surface a synthetic finding so the operator sees the failure
            report.findings.append(Finding(
                id=f"audit.error.{name}",
                category=name,
                severity="info",
                title=f"Audit '{name}' failed to run",
                description=f"The audit raised an exception: {e!r}",
                evidence={"audit": name, "error": repr(e)},
                fix_id=None,
                status="open",
                created_at=now,
            ))
        for f in report.findings:
            await _persist_finding(f, now)
        total += len(report.findings)
        reports.append(report)
    return AuditAggregate(reports=reports, total_findings=total)


@router.post("/audits/{name}", response_model=AuditReport)
async def run_audit(
    _user: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Path(min_length=1, max_length=64)],
) -> AuditReport:
    """Run a single audit by name (no persistence)."""
    fn = REGISTRY.get(name)
    if fn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown audit: {name}")
    return await fn()


@router.get("/findings", response_model=list[Finding])
async def list_findings(
    _user: Annotated[User, Depends(get_current_user)],
    status_: Annotated[str | None, Query(alias="status", max_length=16)] = "open",
) -> list[Finding]:
    """List findings filtered by status (default 'open'; pass 'all' for everything)."""
    if status_ in (None, "", "all"):
        rows = await db.fetchall(
            "SELECT id, category, severity, title, description, evidence, fix_id, status, created_at, updated_at "
            "FROM findings ORDER BY created_at DESC",
        )
    else:
        if status_ not in _VALID_STATUSES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid status: {status_}")
        rows = await db.fetchall(
            "SELECT id, category, severity, title, description, evidence, fix_id, status, created_at, updated_at "
            "FROM findings WHERE status = ? ORDER BY created_at DESC",
            (status_,),
        )
    return [_row_to_finding(r) for r in rows]


@router.post("/findings/{finding_id}/dismiss")
async def dismiss_finding(
    _user: Annotated[User, Depends(get_current_user)],
    finding_id: Annotated[str, Path(min_length=1, max_length=128)],
) -> dict:
    """Mark a finding as dismissed."""
    row = await db.fetchone("SELECT id FROM findings WHERE id = ?", (finding_id,))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "finding not found")
    now = time.time()
    new_status: FindingStatus = "dismissed"
    await db.execute(
        "UPDATE findings SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, now, finding_id),
    )
    return {"ok": True}


@router.post("/findings/{finding_id}/apply-fix")
async def apply_finding_fix(
    _user: Annotated[User, Depends(get_current_user)],
    finding_id: Annotated[str, Path(min_length=1, max_length=128)],
) -> dict:
    """Apply the registered fix for a finding. Phase 7 will wire real fix implementations."""
    row = await db.fetchone("SELECT id, fix_id FROM findings WHERE id = ?", (finding_id,))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "finding not found")
    # 501 Not Implemented surfaced in the body — Phase 7 replaces this stub.
    return {
        "ok": False,
        "message": "apply-fix is not implemented yet (Phase 7 wires real fixes)",
    }
