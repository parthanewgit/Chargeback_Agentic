from __future__ import annotations

from typing import Any


class Repository:
    def __init__(self):
        self.records = []

    def insert(self, item: Any):
        self.records.append(item)
        return item

    def list(self):
        return list(self.records)
