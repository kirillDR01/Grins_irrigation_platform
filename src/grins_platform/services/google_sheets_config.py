"""Google Sheets integration configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleSheetsSettings(BaseSettings):
    """Configuration for Google Sheets polling integration."""

    google_sheets_spreadsheet_id: str = ""
    google_sheets_sheet_name: str = "Form Responses 1"
    google_sheets_poll_interval_seconds: int = 60
    google_service_account_key_path: str = ""
    google_service_account_key_json: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_configured(self) -> bool:
        """Check if required settings are present for polling."""
        return bool(
            self.google_sheets_spreadsheet_id
            and (
                self.google_service_account_key_path
                or self.google_service_account_key_json
            ),
        )
