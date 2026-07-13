import logging
import os
from typing import Protocol

from prefect.blocks.system import Secret
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class SecretProvider(Protocol):
    async def get(self, key: str) -> str | None: ...


class SecretAdapter(Protocol):
    def save(self, key: str, value: str) -> None: ...


class EnvSecretProvider(SecretProvider):
    """Reads from environment variables. Works everywhere (Inngest, local)."""

    async def get(self, key: str) -> str | None:
        import os
        return os.environ.get(key)


class InngestSecretProvider(SecretProvider):
    def __init__(self, env_secret_provider: EnvSecretProvider):
        self.env_secret_provider = env_secret_provider

    async def get(self, key: str) -> str | None:
        # Inngest secrets are available as environment variables in the runtime
        return await self.env_secret_provider.get(key)


class PrefectSecretProvider(SecretProvider):
    async def get(self, key: str) -> str | None:
        normalized_block_name: str = _normalize_block_name(key)
        logger.info(
            "Resolving secret key=%r -> prefect block=%r", key, normalized_block_name
        )

        if normalized_block_name:
            try:
                from prefect.blocks.system import Secret

                secret_block = await Secret.aload(normalized_block_name)
                value = secret_block.get()

                if value:
                    logger.info(
                        "Resolved secret key=%r from Prefect block=%r (len=%d)",
                        key,
                        normalized_block_name,
                        len(value),
                    )
                    return value

                logger.warning(
                    "Prefect block=%r for key=%r exists but returned an empty value; "
                    "falling back to environment variable",
                    normalized_block_name,
                    key,
                )
            except ImportError:
                logger.warning(
                    "Prefect is not installed; cannot load block=%r for key=%r. "
                    "Falling back to environment variable.",
                    normalized_block_name,
                    key,
                )
            except ValueError as exc:
                # Prefect raises ValueError when the block doesn't exist.
                logger.info(
                    "Prefect block=%r not found for key=%r (%s); "
                    "falling back to environment variable",
                    normalized_block_name,
                    key,
                    exc,
                )
            except Exception:
                # Network/API/auth errors — log full traceback for troubleshooting,
                # but never log the secret value.
                logger.exception(
                    "Unexpected error loading Prefect block=%r for key=%r; "
                    "falling back to environment variable",
                    normalized_block_name,
                    key,
                )
        else:
            logger.info(
                "No normalized block name for key=%r; using environment variable only",
                key,
            )

        env_value = os.environ.get(key)
        if env_value:
            logger.info("Resolved secret key=%r from environment variable", key)
        else:
            logger.info(
                "Secret key=%r could not be resolved from Prefect block=%r "
                "or environment variable",
                key,
                normalized_block_name,
            )
        return env_value


class PrefectSecretAdapter(SecretAdapter):
    def save(self, key: str, value: str) -> None:
        normalized_block_name: str = _normalize_block_name(key)
        Secret(value=SecretStr(value)).save(name=normalized_block_name, overwrite=True)


def _normalize_block_name(name: str) -> str:
    result = []
    previous_dash = False

    for char in name.lower():
        if char.isalnum() and char.isascii():
            result.append(char)
            previous_dash = False
        elif not previous_dash:
            result.append("-")
            previous_dash = True

    return "".join(result).strip("-")
