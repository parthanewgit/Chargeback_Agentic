from __future__ import annotations

from app.agents.graph import ChargebackGraph


class DecisionService:
    def __init__(self):
        self.graph = ChargebackGraph()

    def process(self, case, use_llm: bool = True):
        return self.graph.process_case(case, use_llm=use_llm)
