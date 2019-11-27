import os
import urllib

from copy import deepcopy

import pandas as pd
import numpy as np

from autolocal import DocumentManager


documents = DocumentManager()

def add_documents(doc_list_dir):
    doc_list_paths = [os.path.join(doc_list_dir, f) for f in os.listdir(doc_list_dir)]
    for p in doc_list_paths:
        documents.add_docs_from_csv(p)

if __name__=='__main__':

    add_documents(doc_list_dir)