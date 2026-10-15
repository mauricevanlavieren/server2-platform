"""Deterministic examples, deliberately not AI. No model/network dependency."""
from typing import Protocol
from .connectors import Message

LABEL = 'Deterministisch voorbeeld — geen echte AI-uitvoer'

class Processor(Protocol):
    def propose(self, message: Message) -> dict[str, str]: ...

class ExampleProcessor:
    version = 'templates-v1'
    def propose(self, message: Message) -> dict[str, str]:
        # Quoted source is data. Instruction-like text never triggers actions.
        excerpt = message.body.splitlines()[0][:240]
        kind = 'Inkomende vraag' if message.folder == 'inbox' else 'Eerder fictief antwoord'
        actions = {
            'levertijd': 'Ik controleer de gevraagde levertijd voordat ik een datum bevestig.',
            'offerte': 'Ik controleer het product en de aantallen voordat ik een offerte voorstel.',
            'bestelling': 'Ik controleer de gegevens bij het genoemde fictieve ordernummer.',
            'klacht': 'Ik neem de omschrijving van de schade mee voor beoordeling.',
            'techniek': 'Ik laat de technische vraag controleren aan de hand van de productspecificaties.',
            'retour': 'Ik controleer de voorwaarden voordat ik een retour bevestig.',
            'garantie': 'Ik controleer de toepasselijke fictieve garantievoorwaarden.',
            'factuur': 'Ik controleer de referentie op de fictieve factuur.',
            'installatie': 'Ik laat de installatievraag beoordelen voordat ik instructies geef.',
            'follow-up': 'Ik controleer de status van de eerdere aanvraag.',
        }
        action = actions.get(message.topic, 'Ik bekijk uw vraag en controleer de benodigde gegevens.')
        return {'label': LABEL, 'processor_version': self.version,
                'summary': f'{kind} over {message.topic}. Bronfragment: “{excerpt}”',
                'draft': f'Beste demo-contact,\n\nDank voor uw bericht over {message.topic}. {action}\n\nDit is een fictief concept; een medewerker moet de inhoud controleren.\n\nMet vriendelijke groet,\nHet demo-team'}
