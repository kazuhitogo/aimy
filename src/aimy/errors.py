"""Diagnostics. Every message is machine-readable JSON (one object per line)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass
class Diag:
    code: str
    msg: str
    line: int
    col: int
    hint: str | None = None
    severity: str = "error"
    src: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class CompileError(Exception):
    def __init__(self, diags: list[Diag]):
        super().__init__("; ".join(d.msg for d in diags))
        self.diags = diags
