import argparse
import signal
from pathlib import Path
from .connectors import SyntheticConnector
from .processing import ExampleProcessor
from .storage import Store
from .server import DemoServer
from .config import load_config

def main():
    parser=argparse.ArgumentParser(description='Lokale demo met synthetische e-mails; geen mailserver of AI-API.')
    parser.add_argument('--db',type=Path,default=None)
    parser.add_argument('--port',type=int,default=None)
    args=parser.parse_args()
    if args.port is not None and not 1024<=args.port<=65535:parser.error('Gebruik een lokale poort tussen 1024 en 65535.')
    try:
        config=load_config()
        port=args.port if args.port is not None else config.port
        hosts=config.allowed_hosts if args.port is None else (f'127.0.0.1:{port}',f'localhost:{port}')
        store=Store(args.db if args.db is not None else config.db)
        store.import_messages(SyntheticConnector(Path(__file__).resolve().parent.parent/'data/messages.json'),ExampleProcessor())
        if store.counts()['total']!=40:raise ValueError('De database bevat niet exact 40 demoberichten.')
        server=DemoServer(store,port,config.bind,hosts)
    except Exception:
        parser.exit(1,'Start mislukt. Controleer FTS5, de demonstratieset, het databasepad en de lokale poort.\n')
    print(f'Demo actief: http://{config.bind}:{port} — 40 synthetische berichten; geen echte AI; verzenden uitgeschakeld.',flush=True)
    def stop_on_term(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop_on_term)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
