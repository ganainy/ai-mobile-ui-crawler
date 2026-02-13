from dataclasses import dataclass


@dataclass
class MailosaurConfig:
    """Configuration for Mailosaur service."""

    api_key: str
    server_id: str
