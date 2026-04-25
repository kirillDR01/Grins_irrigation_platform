"""WebAuthn / Passkey configuration settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from grins_platform.log_config import get_logger

logger = get_logger(__name__)


class WebAuthnSettings(BaseSettings):
    """Configuration for WebAuthn / Passkey authentication."""

    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Grin's Irrigation"
    webauthn_expected_origins: str = "http://localhost:5173"
    webauthn_challenge_ttl_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def expected_origins_list(self) -> list[str]:
        """Parse comma-separated origins into a list, stripping whitespace."""
        return [
            o.strip() for o in self.webauthn_expected_origins.split(",") if o.strip()
        ]
