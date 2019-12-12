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

from autolocal import AUTOLOCAL_HOME
from autolocal.documentdb import pdf2txt, DocumentManager
from autolocal.parser import nlp


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

class CSVDocumentManager(DocumentManager):
    """
    Class to manage repository of PDF (and TXT) documents        
    """    
    def __init__(
        self,
        document_dir=os.path.join(AUTOLOCAL_HOME, 'data', 'docs'),
        index_dir=os.path.join(AUTOLOCAL_HOME, 'data', 'index'),
        metadata_path=os.path.join(AUTOLOCAL_HOME, 'data', 'index', 'metadata.csv'),
        index_path=os.path.join(AUTOLOCAL_HOME, 'data', 'index', 'index.pkl'),
        force_build_metadata=False,
        force_build_index=False,
        tokenizer_args={},
        index_vars=INDEX_VARS,
        ):

        # store arguments
        self.document_dir = document_dir
        if not os.path.exists(self.document_dir):
            os.makedirs(self.document_dir)
        self.index_dir = index_dir
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)
        self.metadata_path = metadata_path
        self.index_path = index_path
        self.index_vars = index_vars

        # init tokenizer
        self.tokenizer = nlp.Tokenizer(**tokenizer_args)

        # init locks
        self.metadata_lock = threading.RLock()
        self.index_lock = threading.RLock()

        # load metadata from file if it exists
        self.metadata_vars = METADATA_VARS
        self._load_metadata(force_build_metadata)

        # load index from file if it exists
        self._load_index(force_build_index)

        pass

    """
    "Public" methods for reading and writing info from documents
    """

    def get_index(self):
        # Safely return the current value of the index
        with self.index_lock:
            return self.index

    def get_metadata(self):
        # Safely return the current value of the metadata table
        with self.metadata_lock:
            return self.metadata

    def add_doc(
        self,
        new_doc,     
        to_file=True   
        ):
        # add a document to the database.
        # new_doc must be a dict (or row of dataframe) with fields:
        # city, committee, doc_type, date,
        # and optionally, if you want to download and index the document, 
        # url 
        
        doc = {k: np.nan for k in self.metadata_vars}
        doc.update(new_doc)
        doc['date'] = pd.to_datetime(doc['date'])

        # don't add the document if we already have it
        try:
            doc_id = self._get_doc_id(doc)
        except:
            print('warning: could not add document')
            return
        if doc_id in self.metadata.index:
            print('document already added: {}'.format(doc_id))
            return

        # convert non-url
        if not isinstance(doc['url'], str):
            doc['url'] = ''

        # get local paths to document        
        doc_paths = self._get_doc_paths(doc)
        doc.update(doc_paths)

        # download doc from url
        self._download_doc(doc)
            
        # convert to txt
        self._convert_doc(**dict(doc))

        # add to metadata and index
        self._add_doc_to_metadata(doc_id, doc, to_file)

        # if isinstance(doc['url'], str):
        self._add_doc_to_index(doc_id, doc, to_file=to_file)

        print('added document: {}'.format(doc_id))
        
        pass

    def add_docs_from_csv(
        self,
        csv_path,
        pass_fields=None,
        **kwargs
        ):
        # downloads documents specified in csv_path
        # csv must contain fields: city, date, committee, doc_type
        # csv should also contain field `url` in order to download anything        
        docs = pd.read_csv(csv_path, **kwargs)
        for _, row in tqdm(docs.iterrows()):
            self.add_doc(row)
        pass

    def get_count_vector(
        self,        
        key,
        index_var='keyword',
        ):
        # for a given index_var and key, gets a list of (doc_id, count) pairs 
        # and converts to dict of counts with len of metadata

        # initialize vector with same length as metadata
        
        t0 = time()
        with self.metadata_lock:
            with self.index_lock:
                #counts = #np.zeros(len(self.metadata), dtype=int)
                counts = pd.DataFrame(
                    np.array(np.zeros(len(self.metadata), dtype=int)),
                    index=self.metadata.index
                    )

                # see if the key is in the index; if not, return zero vector
                try:
                    values = self.index[index_var][key.upper()]
                except KeyError:
                    t1 = time()
                    print('Returned count vector in time: {}ms'.format((t1-t0)*1000))
                    return np.array(counts.loc[:,0])

                # if key is in index, return the dataframe of counts across documents
                for doc_id, count in values:
                    counts.loc[doc_id,0] = count
                t1 = time()
                print('Returned count vector in time: {}ms'.format((t1-t0)*1000))
                return np.array(counts.loc[:,0])


    """
    Helper functions
    """

    def _load_metadata(self, force_build_metadata=False):
    # if necessary, load metadata from disk or initialize it
        if not force_build_metadata:
            try:
                self.metadata
                return
            except:
                if os.path.exists(self.metadata_path):
                    with self.metadata_lock:
                        self.metadata = pd.read_csv(
                            self.metadata_path,
                            index_col=0,
                            parse_dates=['date']
                            )
                        return
        self._init_metadata()
        return

    def _init_metadata(self):
        # create a metadata file with no data
        metadata = pd.DataFrame({v: [] for v in self.metadata_vars})   
        self._save_metadata(metadata)
        pass

    def _save_metadata(self, metadata, to_file=True):
        with self.metadata_lock:
            self.metadata = metadata
            if to_file:
                self.metadata.to_csv(self.metadata_path)
        pass    
    
    def _add_doc_to_metadata(self, doc_id, doc, to_file=True,):
        # add a single document to the metadata file
        # doc is the record in self.metadata (i.e. one row of the dataframe)
        self._load_metadata()        
        with self.metadata_lock:
            doc_df = pd.DataFrame(doc, index=[doc_id])
            metadata = self.metadata.append(doc_df, sort=False)
            self._save_metadata(metadata, to_file)

    def _load_index(self, force_build_index):
    # if necessary, load index from disk or initialize it
        if not force_build_index:
            try:
                self.index
                return
            except:
                if os.path.exists(self.index_path):
                    with self.index_lock:
                        with open(self.index_path, 'rb') as f:
                            self.index = pkl.load(f)
                        return        
        self._init_index()
        return

    def _init_index(
        self):
        # build the corpus-wide index from scratch, overwriting existing index
        self._load_metadata()
        with self.index_lock:
            self.index = {v: dict() for v in self.index_vars}
        with self.metadata_lock:
            for doc_id, doc in self.metadata.iterrows():
                self._add_doc_to_index(doc_id, doc, to_file=False)
        self._save_index()
        return

    def _save_index(self):
        # save the index to file if called to do so.       
        with open(self.index_path, 'wb') as f:
            with self.index_lock:
                pkl.dump(self.index, f, pkl.HIGHEST_PROTOCOL)
        return

    def _add_item_to_index(self, index_var, key, value):
        # add a single item to the index
        with self.index_lock:
            try:
                self.index[index_var][key].append(value)
            except KeyError:
                self.index[index_var][key] = [value]
            return

    def _add_doc_to_index(self, doc_id, doc, doc_txt=None, to_file=True,):
        # add a single document to the index file
        # doc_id is the row number of the record in self.metadata 
        # doc is the record in self.metadata (i.e. one row of the dataframe)
        try:
            local_path = doc['local_path_txt']
        except:
            return
        if not local_path:
            return

        for index_var in self.index_vars:
            if index_var=='keyword':
                if doc_txt is None:
                    with open(local_path, 'r') as f:
                        doc_txt = f.read()
                tokens = self.tokenizer.tokenize(doc_txt)
                tokens = [t.upper() for t in tokens]
                counter = Counter(tokens)
                for token, count in counter.items():
                    self._add_item_to_index(index_var, token, (doc_id, count))        
        if to_file:
            self._save_index()
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

    def _convert_doc(self, doc):
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


    def _get_city_dir(self, doc):
        # return a file-structure friendly form of a city name
        return doc['city'].lower().replace(' ', '-')


    def _parse_city_dir(self, city_dir): 
        # get city name back from a file-structure friendly version
        return city_dir.replace('-', ' ').title()


    def _get_doc_paths(self, doc):
        orig_format = doc["doc_format"]
        formats = [orig_format, 'txt']
        doc_paths = {'local_path_' + s: '' for s in formats}
        if doc['url']:
            for s in formats:
                k = 'local_path_' + s
                doc_paths[k] = os.path.join(
                    self.document_dir,
                    self._upper(doc['city']),
                    '{}.{}'.format(self._get_doc_id(doc), s)
                )
        return doc_paths

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