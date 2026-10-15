"""Read-only boundary. Future providers normalize to Message before storage."""
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Protocol
import hashlib
import json

CATEGORIES = ('info', 'verkoop', 'support')

@dataclass(frozen=True)
class Message:
    source_id: str
    category: str
    folder: str
    sender: str
    recipient: str
    subject: str
    body: str
    received_at: str
    thread_id: str
    topic: str
    source_hash: str

class MailConnector(Protocol):
    """No send, delete or modify method. Adapters own provider-specific paging."""
    name: str
    def fetch_messages(self) -> tuple[Message, ...]: ...

class SyntheticConnector:
    name = 'synthetic-v1'
    def __init__(self, path: Path):
        self.path = path

    def fetch_messages(self) -> tuple[Message, ...]:
        rows = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(rows, list) or len(rows) != 40:
            raise ValueError('De demonstratieset moet exact 40 berichten bevatten.')
        result = []
        for row in rows:
            if not isinstance(row, dict) or row.get('tenant') != 'demo':
                raise ValueError('Ongeldige demonstratiegegevens.')
            original = dict(row)
            digest = original.pop('hash', None)
            if hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest() != digest:
                raise ValueError('De broncontrole van een demonstratiebericht is mislukt.')
            for field in ('sender', 'recipient', 'mailbox'):
                value = row.get(field)
                if not isinstance(value, str) or not value.rsplit('@', 1)[-1].endswith('.test'):
                    raise ValueError('Alle adressen moeten synthetische .test-adressen zijn.')
            category = row['mailbox'].split('@')[0]
            message = Message(row['id'], category, 'sent' if row['reply_to'] else 'inbox',
                              row['sender'], row['recipient'], row['subject'], row['body'],
                              parsedate_to_datetime(row['date']).astimezone(timezone.utc).isoformat(),
                              row['thread'], row['topic'], digest)
            validate_message(message)
            result.append(message)
        if len({m.source_id for m in result}) != 40:
            raise ValueError('Dubbele bronidentiteit.')
        return tuple(result)

def validate_message(message: Message) -> None:
    if not isinstance(message, Message) or message.category not in CATEGORIES or message.folder not in ('inbox', 'sent'):
        raise ValueError('Ongeldige berichtindeling.')
    for field, limit in [('source_id', 300), ('subject', 500), ('body', 20000), ('sender', 300),
                         ('recipient', 300), ('thread_id', 300), ('topic', 100), ('received_at', 100), ('source_hash', 64)]:
        value = getattr(message, field)
        if not isinstance(value, str) or not value.strip() or len(value) > limit or '\x00' in value:
            raise ValueError('Ongeldige berichtvelden.')
