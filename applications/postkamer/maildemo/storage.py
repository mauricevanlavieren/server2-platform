"""SQLite persistence, FTS5 and optimistic draft edits; no transport code."""
from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone
import re
import sqlite3
from .connectors import MailConnector, validate_message, CATEGORIES
from .processing import Processor

class MissingError(Exception): pass
class ConflictError(Exception): pass

class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY, source TEXT NOT NULL, source_id TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('info','verkoop','support')),
                    folder TEXT NOT NULL CHECK(folder IN ('inbox','sent')),
                    sender TEXT NOT NULL, recipient TEXT NOT NULL, subject TEXT NOT NULL,
                    body TEXT NOT NULL, received_at TEXT NOT NULL, thread_id TEXT NOT NULL,
                    topic TEXT NOT NULL, source_hash TEXT NOT NULL, summary TEXT NOT NULL,
                    example_label TEXT NOT NULL, processor_version TEXT NOT NULL,
                    UNIQUE(source, source_id));
                CREATE VIRTUAL TABLE IF NOT EXISTS message_search USING fts5(
                    subject, body, sender, recipient, tokenize='unicode61 remove_diacritics 2');
                CREATE TABLE IF NOT EXISTS drafts(
                    message_id INTEGER PRIMARY KEY REFERENCES messages(id),
                    text TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL, edited INTEGER NOT NULL DEFAULT 0);
            ''')
        path.chmod(0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def import_messages(self, connector: MailConnector, processor: Processor) -> int:
        messages = tuple(connector.fetch_messages())
        if len({m.source_id for m in messages}) != len(messages):
            raise ValueError('Dubbele bronidentiteit.')
        proposals = []
        for m in messages:
            validate_message(m)
            proposals.append(processor.propose(m))
        count = 0
        with closing(self.connect()) as db, db:
            for m, p in zip(messages, proposals):
                cursor = db.execute('''INSERT INTO messages(source,source_id,category,folder,sender,recipient,
                    subject,body,received_at,thread_id,topic,source_hash,summary,example_label,processor_version)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(source,source_id) DO NOTHING''',
                    (connector.name, m.source_id, m.category, m.folder, m.sender, m.recipient, m.subject,
                     m.body, m.received_at, m.thread_id, m.topic, m.source_hash, p['summary'], p['label'], p['processor_version']))
                if cursor.rowcount:
                    ident = cursor.lastrowid
                    db.execute('INSERT INTO message_search(rowid,subject,body,sender,recipient) VALUES(?,?,?,?,?)',
                               (ident,m.subject,m.body,m.sender,m.recipient))
                    db.execute('INSERT INTO drafts(message_id,text,updated_at) VALUES(?,?,?)',
                               (ident,p['draft'],datetime.now(timezone.utc).isoformat()))
                    count += 1
        return count

    def search(self, query='', category='', folder=''):
        if not isinstance(query, str) or len(query) > 200:
            raise ValueError('Zoektekst mag maximaal 200 tekens bevatten.')
        if category not in ('', *CATEGORIES) or folder not in ('', 'inbox', 'sent'):
            raise ValueError('Ongeldig filter.')
        terms = re.findall(r'\w+', query, flags=re.UNICODE)
        if len(terms) > 20:
            raise ValueError('Gebruik maximaal 20 zoekwoorden.')
        if query.strip() and not terms:
            return []
        where, args = [], []
        join = ''
        if terms:
            join = ' JOIN message_search ON message_search.rowid=m.id '
            where.append('message_search MATCH ?')
            args.append(' AND '.join('"'+t+'"' for t in terms))
        for key, value in [('category', category), ('folder', folder)]:
            if value:
                where.append(f'm.{key}=?'); args.append(value)
        sql = 'SELECT m.id,m.category,m.folder,m.sender,m.recipient,m.subject,m.received_at,substr(m.body,1,130) AS preview,d.edited FROM messages m JOIN drafts d ON d.message_id=m.id'+join
        if where: sql += ' WHERE '+' AND '.join(where)
        sql += ' ORDER BY m.received_at DESC,m.id DESC LIMIT 100'
        with closing(self.connect()) as db:
            return [dict(r) for r in db.execute(sql,args)]

    def counts(self):
        with closing(self.connect()) as db:
            return {'total': db.execute('SELECT count(*) FROM messages').fetchone()[0],
                    'categories':dict(db.execute('SELECT category,count(*) FROM messages GROUP BY category')),
                    'folders':dict(db.execute('SELECT folder,count(*) FROM messages GROUP BY folder'))}

    def detail(self, ident):
        with closing(self.connect()) as db:
            row = db.execute('''SELECT m.*,d.text AS draft,d.version AS draft_version,d.edited,
                d.updated_at FROM messages m JOIN drafts d ON d.message_id=m.id WHERE m.id=?''',(ident,)).fetchone()
            if row is None: raise MissingError()
            return dict(row)

    def save_draft(self, ident, text, version):
        if not isinstance(text, str) or not text.strip() or len(text) > 10000 or '\x00' in text:
            raise ValueError('Een concept moet 1–10.000 tekens bevatten.')
        if type(version) is not int or version < 1:
            raise ValueError('Ongeldige conceptversie.')
        with closing(self.connect()) as db, db:
            if db.execute('SELECT 1 FROM messages WHERE id=?',(ident,)).fetchone() is None:
                raise MissingError()
            result = db.execute('UPDATE drafts SET text=?,version=version+1,edited=1,updated_at=? WHERE message_id=? AND version=?',
                                (text,datetime.now(timezone.utc).isoformat(),ident,version))
            if result.rowcount != 1: raise ConflictError()
            row = db.execute('''SELECT m.*,d.text AS draft,d.version AS draft_version,d.edited,
                d.updated_at FROM messages m JOIN drafts d ON d.message_id=m.id WHERE m.id=?''',(ident,)).fetchone()
            saved = dict(row)
        return saved

    def health(self):
        with closing(self.connect()) as db:
            count=db.execute('SELECT count(*) FROM messages').fetchone()[0]
            indexed=db.execute('SELECT count(*) FROM message_search').fetchone()[0]
            db.execute("SELECT rowid FROM message_search WHERE message_search MATCH 'demo' LIMIT 1").fetchall()
            if count != indexed: raise sqlite3.DatabaseError('index mismatch')
            return {'status':'ok','mode':'synthetic-only','messages':count,'fts5':True,'sending':False,'external_ai':False}
