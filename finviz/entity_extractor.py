
"""
Entity extraction helper that uses OpenRouter with the Gemini model to pull
financial tickers and contextual constraints from analyst-style prompts.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Load environment variables from a local .env file if present.
load_dotenv()

SYSTEM_PROMPT = """
You are a financial entity extraction assistant.
Extract company tickers (uppercase) and contextual constraints from user requests.
Always reply with a valid JSON object:
{"Tickers": ["..."], "Companies": ["..."], "Context": ["..."]}

Rules:
- Include tickers explicitly named or implied (competitors, suppliers, indices).
- For every company name, include the most likely primary ticker as it would appear on Finviz. If non-US, prefer the Finviz/US ADR symbol when available; otherwise use exchange-qualified form (e.g., AMS:FLOW, LON:ULVR). Prefer the most liquid/common share class.
- Include company names as strings (prefer official/long names when present).
- "Context" holds time periods, events, regions, industries, or constraints that guide analysis.
- If nothing fits a section, return an empty array for that key.
- Do not include explanations or extra text outside the JSON.
"""


class ExtractionResponse(BaseModel):
    tickers: List[str] = Field(default_factory=list, alias="Tickers")
    companies: List[str] = Field(default_factory=list, alias="Companies")
    context: List[str] = Field(default_factory=list, alias="Context")

    class Config:
        populate_by_name = True

    def as_dict(self) -> Dict[str, List[str]]:
        return self.model_dump(by_alias=True)


class EntityExtractor:
    """
    Wraps an OpenRouter LLM call and exposes a simple `extract` method.

    Example:
        extractor = EntityExtractor()
        result = extractor.extract("Analyze Nvidia and its competitors during the 2008 crisis")
        print(result.model_dump(by_alias=True))
        # {"Tickers": ["NVDA", "AMD", ...], "Companies": ["NVIDIA", "Advanced Micro Devices", ...], "Context": ["2008 crisis"]}
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY is required. Set it in the environment or .env file.")

        self.model = model or os.environ.get("MODEL", "google/gemini-2.5-flash-lite")
        self.base_url = base_url or os.environ.get("GPT_URL", "https://openrouter.ai/api/v1")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _build_prompt(self, user_prompt: str) -> str:
        return (
            f"User query: {user_prompt}\n"
            "Extract:\n"
            "- List every relevant company ticker (explicitly named or implied peers/benchmarks). Always include a ticker for each company name, using the form Finviz would display. For non-US names, prefer the US ADR/Finviz ticker; if none, use exchange-qualified (e.g., AMS:FLOW, LON:ULVR). Use uppercase tickers.\n"
            "- Company names (long or short) corresponding to the tickers or entities mentioned; include competitors/suppliers/benchmarks if implied.\n"
            "- Contextual constraints that narrow analysis (periods, events, geographies, sectors).\n"
            "Respond with JSON only, shaped as:\n"
            '{"Tickers": ["..."], "Companies": ["..."], "Context": ["..."]}\n'
            "Use empty arrays if a section has no items."
        )

    def _parse_response(self, content: str) -> ExtractionResponse:
        def _load_json(text: str) -> Dict[str, List[str]]:
            # Attempt to parse the full string; if it fails, try extracting the first JSON object.
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", text, flags=re.DOTALL)
                if not match:
                    raise
                return json.loads(match.group(0))

        data = _load_json(content)
        tickers = [str(t).upper() for t in data.get("Tickers", []) if str(t).strip()]
        companies = [str(c).strip() for c in data.get("Companies", []) if str(c).strip()]
        context = [str(c).strip() for c in data.get("Context", []) if str(c).strip()]
        return ExtractionResponse(tickers=tickers, companies=companies, context=context)

    def extract(self, prompt: str) -> ExtractionResponse:
        """
        Extract tickers and contextual constraints from a natural language prompt.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(prompt)},
        ]

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )
        content = completion.choices[0].message.content or "{}"
        return self._parse_response(content)
