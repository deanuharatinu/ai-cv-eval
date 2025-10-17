from typing import Protocol


class LLMClient(Protocol):
    async def generate_json(self, prompt: str, schema: dict) -> dict:
        ...


class MockLLMClient(LLMClient):
    async def generate_json(self, prompt: str, schema: dict) -> dict:
        # TODO: integrate ADK powered orchestration with a real model.
        return {"mock": True}
