#!/usr/bin/env python3
"""Bind verification claims to local receipts and current subject fingerprints."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

KINDS = {"automatic", "ai", "human"}
STATUSES = {"passed", "failed", "not_run"}


class EvidenceError(ValueError):
    pass


def local_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise EvidenceError("evidence paths must be relative to the evidence root")
    root = root.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path == root:
        raise EvidenceError("evidence path escapes the evidence root")
    return path


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_digest(value: object) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise EvidenceError("invalid SHA256 fingerprint")


def verify_bundle(bundle: dict, root: Path) -> dict:
    if not isinstance(bundle, dict) or set(bundle) != {"version", "checks"} or bundle["version"] != 1:
        raise EvidenceError("unsupported evidence bundle")
    checks = bundle["checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= 3:
        raise EvidenceError("expected one to three verification dimensions")
    states = {kind: "not_run" for kind in sorted(KINDS)}
    seen = set()
    for check in checks:
        if not isinstance(check, dict):
            raise EvidenceError("invalid verification dimension")
        kind, status = check.get("kind"), check.get("status")
        if not isinstance(kind, str) or kind not in KINDS or kind in seen or status not in STATUSES:
            raise EvidenceError("invalid or duplicate verification dimension")
        seen.add(kind)
        if status == "not_run":
            if set(check) != {"kind", "status"}:
                raise EvidenceError("unperformed verification cannot claim a receipt")
            continue
        if set(check) != {"kind", "status", "receipt", "sha256"}:
            raise EvidenceError("executed verification needs a receipt and fingerprint")
        check_digest(check["sha256"])
        path = local_path(root, check["receipt"])
        if path.stat().st_size > 65536 or fingerprint(path) != check["sha256"]:
            raise EvidenceError("receipt changed or exceeds size limit")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or receipt.get("version") != 1 or receipt.get("kind") != kind or receipt.get("status") != status:
            raise EvidenceError("receipt does not match the claimed result")
        if not isinstance(receipt.get("method"), str) or not receipt["method"].strip():
            raise EvidenceError("receipt needs the command or assessment method")
        try:
            checked_at = datetime.fromisoformat(receipt["checked_at"].replace("Z", "+00:00"))
            if checked_at.tzinfo is None:
                raise ValueError("timezone required")
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise EvidenceError("receipt needs a timestamp with timezone") from exc
        subjects = receipt.get("subjects")
        if not isinstance(subjects, list) or not subjects:
            raise EvidenceError("receipt needs checked subjects")
        for subject in subjects:
            if not isinstance(subject, dict) or set(subject) != {"path", "sha256"}:
                raise EvidenceError("invalid checked subject")
            check_digest(subject["sha256"])
            if fingerprint(local_path(root, subject["path"])) != subject["sha256"]:
                raise EvidenceError("checked subject changed; rerun relevant verification")
        if kind == "automatic":
            code = receipt.get("exit_code")
            if type(code) is not int or (status == "passed") != (code == 0):
                raise EvidenceError("automatic result conflicts with command exit code")
        else:
            # This binds an assessment artifact, not the identity or judgment of its author.
            reference = receipt.get("assessment")
            if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
                raise EvidenceError("AI/human assessment needs a source artifact")
            check_digest(reference["sha256"])
            if fingerprint(local_path(root, reference["path"])) != reference["sha256"]:
                raise EvidenceError("assessment artifact changed")
        states[kind] = status
    return states


def run_check(root: Path, subjects: list[str], receipt_name: str, command: list[str], timeout: float = 120) -> dict:
    if not command or not subjects or timeout <= 0:
        raise EvidenceError("a command, subjects, and positive timeout are required")
    root = root.resolve()
    destination = local_path(root, receipt_name)
    if destination.exists():
        raise EvidenceError("use a new receipt path; existing evidence is immutable")
    before = [{"path": name, "sha256": fingerprint(local_path(root, name))} for name in subjects]
    if any(local_path(root, s["path"]) == destination for s in before):
        raise EvidenceError("receipt cannot also be a checked subject")
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            result = subprocess.run(command, cwd=root, stdout=stdout, stderr=stderr, timeout=timeout, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
        for subject in before:
            if fingerprint(local_path(root, subject["path"])) != subject["sha256"]:
                raise EvidenceError("subject changed during verification; no receipt written")
        output_hashes = {}
        for label, stream in (("stdout", stdout), ("stderr", stderr)):
            stream.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(65536), b""):
                digest.update(chunk)
            output_hashes[label + "_sha256"] = digest.hexdigest()
    receipt = {
        "version": 1, "kind": "automatic", "status": "passed" if code == 0 else "failed",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "method": json.dumps(command, ensure_ascii=False), "exit_code": code,
        "subjects": before, **output_hashes,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"kind": "automatic", "status": receipt["status"], "receipt": receipt_name, "sha256": fingerprint(destination)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--subject", action="append", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    check = run_check(args.root, args.subject, args.receipt, command, args.timeout)
    print(json.dumps({"version": 1, "checks": [check]}, ensure_ascii=False))
    return 0 if check["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
