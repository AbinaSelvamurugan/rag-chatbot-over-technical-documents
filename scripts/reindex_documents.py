"""Explicit safe re-index of persisted source bytes; no global reset."""
import argparse
from backend.app.main import services

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('document_id')
    args=parser.parse_args()
    print(services()[0].reindex(args.document_id))

if __name__=='__main__': main()
