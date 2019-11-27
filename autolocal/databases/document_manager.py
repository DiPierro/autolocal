import os
from collections import Counter
from datetime import datetime
import threading
import pickle as pkl
from time import time

import pandas as pd
import numpy as np
from urllib.request import urlretrieve
from tqdm import tqdm

from autolocal.pdf2txt import pdf2txt
from autolocal import nlp

INDEX_VARS = ['keyword']
METADATA_VARS = [
    'city',
    'committee',
    'date',
    'doc_type',
    'meeting_type',
    'url',
    'local_path_pdf',
    'local_path_txt',
    'doc_format'
]

class DocumentManager():
    """
    Class to manage repository of PDF (and TXT) documents        
    """    

    def __init__(self, **kwargs):
        self.index = None
        self.metadata = None
        pass

    """
    Ways of converting database information to unique, file-structure-friendly strings
    """

    def get_index(self):
        return self.index

    def get_metadata(self):
        return self.metadata

    def _lower(self, city_name):
        # return a file-structure friendly form of a city name
        return city_name.lower().replace(' ', '-')

    def _upper(self, city_name): 
        # get city name back from a file-structure friendly version
        return city_name.replace('-', ' ').title()        

    def _get_doc_id(self, **doc):
        # produce the file name which the document will be known by locally.
        # `doc` variable must contain fields:  city, date, committee        
        date = doc['date'].strftime('%Y-%m-%d')
        city = doc['city'].title().replace(' ', '-')
        committee = doc['committee'].title().replace(' ', '-')
        if isinstance(doc['meeting_type'], str):
            meeting_type = doc['meeting_type'].title().replace(' ', '-')
        else:
            meeting_type = None
        doc_type = doc['doc_type'].title().replace(' ', '-')
        identifiers = ["{}".format(x) for x in [city, date, committee, meeting_type, doc_type] if x]
        return '_'.join(identifiers)

    def _parse_doc_id(self, doc_id):
        # given a file name, extract the document properties
        city, date, committee, doc_type = fname.split('_')
        city = city.replace('-', ' ')
        committee = committee.replace('-', ' ')
        date = datetime.strptime(date, '%Y-%m-%d').date()
        doc_type = doc_type.replace('-', ' ')
        return city, date, committee, doc_type

    def _convert_doc(self, **doc):
        # convert a pdf to txt and save in designated location
        try:
            if doc['doc_format'] == 'pdf':
                pdf_path = doc['local_path_pdf']
            elif doc['doc_format'] == 'html':
                html_path= doc['local_path_html']
            txt_path = doc['local_path_txt']
        except KeyError:
            return
        if not txt_path:
            return
        if os.path.exists(txt_path):
            print('... path already exists: {}'.format(txt_path))
            return

        # make directories if they don't yet exist
        os.makedirs(os.path.split(txt_path)[0], exist_ok=True)
        
        if doc['doc_format'] == "pdf":
            # convert pdf
            try:
                args = [pdf_path, '-o', txt_path]
                pdf2txt(args)
            except:
                return
            return
        else:
            # convert html
            # TODO
            return        

    def _download_doc(self, doc):
        # download a document from given url to designated local location
        try:
            doc_format = doc['doc_format']
            local_path_key = 'local_path_{}'.format(doc_format)
            local_path = doc[local_path_key]
            url = doc['url']
        except KeyError:
            return
        if not (url and local_path):
            return
        if os.path.exists(local_path):
            print('... path already exists: {}'.format(local_path))
            return

        # make directories if they don't yet exist
        os.makedirs(os.path.split(local_path)[0], exist_ok=True)

        # download pdf
        try:
            urlretrieve(url.replace(' ', '%20'), local_path)
        except:
            print('warning: could not retrieve html')
            print(url)

        return
