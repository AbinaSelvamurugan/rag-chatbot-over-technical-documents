"""Ingest original local corpus or a custom directory with the production index."""
from pathlib import Path
import argparse
from backend.app.main import services
from backend.app.services.extraction import EXTENSIONS

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dir',type=Path,default=Path('data/sample_documents'))
    p.add_argument('--collection',default='default')
    args=p.parse_args()
    ingest,_,_,_=services()
    for path in sorted(args.dir.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS: continue
        try:
            result=ingest.ingest(path.name,path.read_bytes(),args.collection)
            print(f"{result['title']}: {result['status']} ({result['chunks']} chunks, duplicate={result['duplicate']})")
        except Exception as e:
            print(f'{path.name}: failed ({type(e).__name__}: {e})')

if __name__=='__main__': main()
