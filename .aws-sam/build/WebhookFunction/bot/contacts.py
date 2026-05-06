"""Contact management helpers."""

from typing import Dict, List, Optional

from bot.db.contacts import ContactsDB
from bot.utils.validation import validate_wallet_address


class ContactsService:
    """High-level contact operations with validation."""

    def __init__(self, db: ContactsDB):
        self.db = db

    def list_contacts(self, user_id: str) -> List[Dict]:
        return self.db.get_contacts(user_id)

    def add_contact(self, user_id: str, name: str, address: str) -> str:
        if not name or not name.strip():
            raise ValueError("Contact name cannot be empty.")
        valid, error = validate_wallet_address(address)
        if not valid:
            raise ValueError(error or "Invalid wallet address.")
        return self.db.add_contact(user_id, name.strip(), address.strip())

    def remove_contact(self, user_id: str, contact_id: str) -> None:
        self.db.remove_contact(user_id, contact_id)

    def resolve_name_or_address(self, user_id: str, value: str) -> Optional[str]:
        if not value:
            return None
        for contact in self.list_contacts(user_id):
            if contact.get("name", "").lower() == value.lower():
                return contact.get("address")
        valid, _ = validate_wallet_address(value)
        return value if valid else None

