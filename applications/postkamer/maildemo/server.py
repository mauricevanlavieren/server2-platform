"""Small JSON/HTML server for one local demo operator; explicit container binding."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from pathlib import Path
import json
import logging
import re
import sqlite3
from .storage import Store, MissingError, ConflictError

STATIC = Path(__file__).parent/'static'

class Handler(BaseHTTPRequestHandler):
    server_version = 'MailDemo'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format, *args):
        # Do not log request bodies, search terms, addresses or drafts.
        pass

    def respond(self, code, body, content_type='application/json; charset=utf-8'):
        if not isinstance(body, bytes): body=json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        for name,value in {'Content-Type':content_type,'Content-Length':str(len(body)),
                           'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                           'Referrer-Policy':'no-referrer',
                           'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"}.items():
            self.send_header(name,value)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass

    def check_host(self):
        port=self.server.server_address[1]
        return self.headers.get('Host') in self.server.allowed_hosts

    def handle_api(self, write=False):
        if not self.check_host():
            self.respond(403,{'error':'Deze demo is alleen lokaal toegankelijk.'});return
        try:
            url=urlsplit(self.path)
            if url.netloc or url.scheme: raise ValueError('Ongeldig verzoek.')
            if not write:
                if url.path in ('/','/app.js','/style.css'):
                    name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[url.path]
                    mime={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[url.path]
                    self.respond(200,(STATIC/name).read_bytes(),mime);return
                if url.path=='/healthz':self.respond(200,self.server.store.health());return
                if url.path=='/api/messages':
                    params=parse_qs(url.query,keep_blank_values=True,max_num_fields=4)
                    if set(params)-{'q','category','folder'} or any(len(v)!=1 for v in params.values()):
                        raise ValueError('Ongeldige zoekparameters.')
                    get=lambda key:params.get(key,[''])[0]
                    self.respond(200,{'items':self.server.store.search(get('q'),get('category'),get('folder')),'counts':self.server.store.counts()});return
                match=re.fullmatch(r'/api/messages/([1-9][0-9]{0,8})',url.path)
                if match:self.respond(200,self.server.store.detail(int(match[1])));return
            else:
                port=self.server.server_address[1]
                if self.headers.get('Origin') != 'http://' + self.headers.get('Host', ''):
                    self.respond(403,{'error':'Opslaan vereist dezelfde lokale oorsprong.'});return
                match=re.fullmatch(r'/api/messages/([1-9][0-9]{0,8})/draft',url.path)
                if match:
                    if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Length'):
                        raise ValueError('Ongeldige verzoeklengte.')
                    size=int(self.headers['Content-Length'])
                    if size<1 or size>32768:self.respond(413,{'error':'Het verzoek is te groot of leeg.'});return
                    if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
                        self.respond(415,{'error':'Gebruik JSON.'});return
                    raw=self.rfile.read(size)
                    if len(raw)!=size: raise ValueError('Onvolledig verzoek.')
                    payload=json.loads(raw)
                    if not isinstance(payload,dict) or set(payload)!={'text','version'}:
                        raise ValueError('Verwacht uitsluitend text en version.')
                    self.respond(200,self.server.store.save_draft(int(match[1]),payload['text'],payload['version']));return
            self.respond(404,{'error':'Niet gevonden. Verzenden is niet beschikbaar.'})
        except MissingError:self.respond(404,{'error':'Bericht niet gevonden.'})
        except ConflictError:self.respond(409,{'error':'Dit concept is elders gewijzigd. Heropen het bericht vóór opslaan.'})
        except (ValueError,UnicodeDecodeError):self.respond(400,{'error':'Ongeldige invoer. Controleer filters of conceptvelden.'})
        except TimeoutError:self.respond(408,{'error':'Het verzoek duurde te lang.'})
        except (sqlite3.Error,OSError):
            logging.error('Lokale opslag of statische bestanden niet beschikbaar; geen inhoud gelogd.')
            self.respond(503,{'error':'De lokale opslag is tijdelijk niet beschikbaar.'})
        except Exception:
            logging.error('Onverwachte applicatiefout; geen verzoekinhoud gelogd.')
            self.respond(500,{'error':'Het verzoek kon niet veilig worden verwerkt.'})

    def do_GET(self):self.handle_api()
    def do_PATCH(self):self.handle_api(write=True)
    def do_POST(self):self.respond(405,{'error':'Deze actie is niet beschikbaar. Er worden geen e-mails verzonden.'})
    do_DELETE=do_POST
    do_PUT=do_POST

class DemoServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self, store: Store, port=8765, bind='127.0.0.1', allowed_hosts=None):
        self.store=store
        if bind not in ('127.0.0.1','0.0.0.0'):raise ValueError('Ongeldige binding')
        super().__init__((bind,port),Handler)
        actual=self.server_address[1]
        self.allowed_hosts=tuple(allowed_hosts) if allowed_hosts is not None else (f'127.0.0.1:{actual}',f'localhost:{actual}')
