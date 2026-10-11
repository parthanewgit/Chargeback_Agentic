from __future__ import annotations

from typing import Any

from app.tools.registry import ToolRegistry


class Investigator:
    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or ToolRegistry()

    def run(self, plan: dict[str, Any]) -> dict[str, Any]:
        if plan.get('action') != 'call_tool':
            return {'status': 'stopped'}
        tool_name = plan.get('tool_name')
        args = plan.get('arguments', {})
        return self.registry.call(tool_name, **args)
