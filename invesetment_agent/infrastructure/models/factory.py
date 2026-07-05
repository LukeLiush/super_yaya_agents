from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional

from prefect.blocks.system import Secret

from invesetment_agent.application.port.model_provider import ModelProvider


@dataclass(frozen=True)
class _ProviderSpec:
    """Bundles everything that must stay consistent for one provider:
    how to recognize its models, which secret holds its key, and how to build it."""
    name: str
    matches: Callable[[str], bool]
    secret_name: str  # Prefect Secret block name
    env_var: str  # fallback env var for local dev
    build: Callable[[str, str], object]  # (model_name, api_key) -> pydantic-ai model


# --- Provider builders: the ONLY place pydantic-ai providers are imported ---

def _build_pydantic_ai_google(model_name: str, api_key: str) -> object:
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider
    return GoogleModel(model_name.split("pydantic:")[1].replace("-lite", ""), provider=GoogleProvider(api_key=api_key))


def _build_agno_google(model_name: str, api_key: str) -> object:
    from agno.models.google import Gemini
    # Map model names if necessary, e.g., 'gemini-1.5-flash'
    return Gemini(id=model_name.split("agno:")[1], api_key=api_key)


# --- Registry: add a provider by adding one fully-specified entry ---

_PROVIDERS: list[_ProviderSpec] = [
    _ProviderSpec(
        name="pydantic-google",
        matches=lambda n: n.startswith("pydantic:gemini") or n.startswith("pydantic:google"),
        secret_name="google-api-key",
        env_var="GOOGLE_API_KEY",
        build=_build_pydantic_ai_google,
    ),
    _ProviderSpec(
        name="agno-google",
        matches=lambda n: n.startswith("agno:gemini") or n.startswith("agno:google"),
        secret_name="google-api-key",
        env_var="GOOGLE_API_KEY",
        build=_build_agno_google,
    ),
]


class ConfiguredModelProvider(ModelProvider):
    """Infrastructure adapter that builds a pydantic-ai model from a model name.

    The API key is derived FROM the model name (never passed in), so an OpenAI key
    can never be paired with a Google model — the pairing is enforced by construction.

    Keys are loaded from a Prefect Secret block, falling back to an environment
    variable for local development.
    """

    def __init__(self, prefer_env_first: bool = False) -> None:
        self._prefer_env_first = prefer_env_first

    def get_model(self, model_name: str) -> object:
        spec = self._resolve_spec(model_name)
        api_key = self._load_key(spec)
        return spec.build(model_name, api_key)

    # --- internals ---
    def _resolve_spec(self, model_name: str) -> _ProviderSpec:
        for spec in _PROVIDERS:
            if spec.matches(model_name):
                return spec
        supported = ", ".join(s.name for s in _PROVIDERS)
        raise ValueError(
            f"Unsupported model: {model_name!r}. "
            f"No provider matches it (known providers: {supported})."
        )

    def _load_key(self, spec: _ProviderSpec) -> str:
        # try the two sources in the configured order
        sources = (
            [self._from_env, self._from_secret]
            if self._prefer_env_first
            else [self._from_secret, self._from_env]
        )
        for source in sources:
            key = source(spec)
            if key:
                return key
        raise RuntimeError(
            f"No API key for provider {spec.name!r}: expected Prefect Secret "
            f"{spec.secret_name!r} or env var {spec.env_var!r} to be set."
        )

    @staticmethod
    def _from_secret(spec: _ProviderSpec) -> Optional[str]:
        try:
            return Secret.load(spec.secret_name).get()
        except Exception:
            return None  # block missing / no server reachable -> fall back

    @staticmethod
    def _from_env(spec: _ProviderSpec) -> Optional[str]:
        return os.environ.get(spec.env_var)
