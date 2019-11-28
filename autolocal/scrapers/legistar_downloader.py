import os
import argparse
from autolocal.databases import S3DocumentManager

documents = S3DocumentManager()

def add_documents(doc_list_dir):
    doc_list_paths = [os.path.join(doc_list_dir, f) for f in os.listdir(doc_list_dir)]
    print('Found paths:')
    print('\n'.join(doc_list_paths))
    for p in doc_list_paths:
        documents.add_docs_from_csv(p)

if __name__=='__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('doc_list_dir')
    args = parser.parse_args()
    
    add_documents(args.doc_list_dir)

    