"""Run annotated retrieval evaluation and persist JSON run artifact."""
import argparse
from pathlib import Path
from backend.app.main import services
from backend.app.services.evaluation import evaluate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--k',type=int,default=5)
    parser.add_argument('--generate',action='store_true')
    args=parser.parse_args()
    _,retriever,rag,_=services()
    result=evaluate(Path('evaluation/dataset/local_questions.json'),Path('evaluation/results'),retriever,rag,args.k,args.generate)
    print(result['run_id'])
    print(result['macro_document_metrics'])

if __name__=='__main__':main()
