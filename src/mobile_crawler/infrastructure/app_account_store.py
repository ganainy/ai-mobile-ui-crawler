"""Per-app-package App Account storage (see CONTEXT.md).

Username and address override live in plain settings; the password is stored
encrypted in the secrets table. There is deliberately no global fallback.
"""

from dataclasses import dataclass

from mobile_crawler.infrastructure.user_config_store import UserConfigStore


@dataclass(frozen=True)
class AppAccount:
    """Login for one app. `address_override` is the email address to use instead of the default."""

    username: str
    password: str
    address_override: str = ""


def app_account_config_key(app_package: str) -> str:
    return f"app_account::{app_package}"


def app_account_password_key(app_package: str) -> str:
    return f"app_account_password::{app_package}"


class AppAccountStore:
    """Reads and writes the App Account of each app package."""

    def __init__(self, user_config_store: UserConfigStore):
        self._store = user_config_store

    def get(self, app_package: str) -> AppAccount | None:
        data = self._store.get_setting(app_account_config_key(app_package))
        if not isinstance(data, dict) or not data.get("username"):
            return None
        password = self._store.get_secret_plaintext(app_account_password_key(app_package)) or ""
        return AppAccount(
            username=str(data["username"]),
            password=password,
            address_override=str(data.get("address_override") or ""),
        )

    def save(self, app_package: str, account: AppAccount) -> None:
        self._store.set_setting(
            app_account_config_key(app_package),
            {"username": account.username, "address_override": account.address_override},
            "json",
        )
        if account.password:
            self._store.set_secret_plaintext(app_account_password_key(app_package), account.password)
        else:
            self._store.delete_secret(app_account_password_key(app_package))

    def delete(self, app_package: str) -> None:
        self._store.delete_setting(app_account_config_key(app_package))
        self._store.delete_secret(app_account_password_key(app_package))
