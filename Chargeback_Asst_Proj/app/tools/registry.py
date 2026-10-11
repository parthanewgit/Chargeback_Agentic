from __future__ import annotations

from typing import Any

from app.tools.mock_tools import get_customer_history, get_delivery_status, get_merchant_profile, get_prior_disputes, get_transaction

TOOL_ALLOWLIST = {
    'get_transaction': get_transaction,
    'get_customer_history': get_customer_history,
    'get_delivery_status': get_delivery_status,
    'get_prior_disputes': get_prior_disputes,
    'get_merchant_profile': get_merchant_profile,
}


class ToolRegistry:
    def __init__(self):
        self.tools = TOOL_ALLOWLIST.copy()

    def list_tools(self) -> list[str]:
        return sorted(self.tools.keys())

    def call(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        if tool_name not in self.tools:
            raise ValueError(f'Unsupported tool name: {tool_name}')
        return self.tools[tool_name](**kwargs)
