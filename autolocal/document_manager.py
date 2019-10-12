import os
from collections import Counter
from datetime import datetime
import threading
import pickle as pkl

import pandas as pd
import numpy as np
from urllib.request import urlretrieve
from tqdm import tqdm

from autolocal.pdf2txt import pdf2txt
from autolocal.nlp import Tokenizer

INDEX_VARS = ['keyword']
METADATA_VARS = [
    'city',
    'committee',
    'date',
    'doc_type',
    'url',
    'local_path_pdf',
    'local_path_txt'
]

class DocumentManager(object):
    """
    Class to manage repository of PDF (and TXT) documents        
    """    
    def __init__(
        self,
        document_dir='../data/docs',
        index_dir='../data/index',
        metadata_path='../data/index/metadata.csv',
        index_path='../data/index/index.pkl',
        force_build_metadata=False,
        force_build_index=False,
        tokenizer_args={},
        index_vars=INDEX_VARS,
        ):

        # store arguments
        self.document_dir = os.path.abspath(document_dir)
        if not os.path.exists(self.document_dir):
            os.mkdir(self.document_dir)
        self.index_dir = os.path.abspath(index_dir)
        if not os.path.exists(self.index_dir):
            os.mkdir(self.index_dir)
        self.metadata_path = os.path.abspath(metadata_path)
        self.index_path = os.path.abspath(index_path)
        self.index_vars = index_vars

        # init tokenizer
        self.tokenizer = Tokenizer(**tokenizer_args)

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
        # self, city, committee, doc_type, date,
        # and optionally, if you want to download and index the document, 
        # url 
        
        # create dict for doc
        doc = {k: np.nan for k in self.metadata_vars}
        doc.update(new_doc)
        doc['date'] = pd.to_datetime(doc['date'])

        # if url exists, download and process document
        if isinstance(doc['url'], str):
            # get local paths to document
            doc_paths = self._write_doc_paths(doc)
            doc.update(doc_paths)

            # download doc from url
            self._download_doc(doc)
            
            # convert to txt
            self._convert_doc(doc)

        # add to metadata and index
        doc_id = self._add_doc_to_metadata(doc)

        if isinstance(doc['url'], str):
            self._add_doc_to_index(doc_id, doc)

        pass

    def add_docs_from_csv(
        self,
        csv_path,
        pass_fields=None,
        ):
        # downloads documents specified in csv_path
        # csv must contain fields: city, date, committee, doc_type
        # csv should also contain field `url` in order to download anything        
        docs = pd.read_csv(csv_path)
        for _, row in tqdm(docs.iterrows()):
            self.add_doc(row)
        pass

    def get_count_vector(
        self,        
        key,
        index_var='keyword',        
        ):
        # for a given index_var and key, gets a list of (doc_id, count) pairs 
        # and converts to vector of counts with len of metadata

        # initialize vector with same length as metadata
        with self.metadata_lock:
            with self.index_lock:
                counts = np.zeros(len(self.metadata), dtype=int)

                # see if the key is in the index; if not, return zero vector
                try:
                    values = self.index[index_var][key.upper()]
                except KeyError:            
                    return counts

                # if key is in index, return the vector of counts across documents
                for doc_id, count in values:
                    counts[doc_id] = count
                return counts

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
                        self.metadata = pd.read_csv(self.metadata_path)
                        return            
        self._init_metadata()
        return

    def _init_metadata(self):
        # create a metadata file with no data
        metadata = pd.DataFrame({v: [] for v in self.metadata_vars})        
        self._save_metadata(metadata)
        pass

    def _save_metadata(self, metadata):
        with self.metadata_lock:
            self.metadata = metadata
            self.metadata.to_csv(self.metadata_path)
        pass    
    
    def _add_doc_to_metadata(self, doc, to_file=True,):
        # add a single document to the metadata file
        # doc is the record in self.metadata (i.e. one row of the dataframe)
        self._load_metadata()        
        with self.metadata_lock:
            doc_id = len(self.metadata)
            doc_df = pd.DataFrame(doc, index=[doc_id])
            metadata = self.metadata.append(doc_df, sort=False)
            self._save_metadata(metadata)        
        return doc_id

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

    def _save_index(self):
        # save the index to file if called to do so.       
        with open(self.index_path, 'wb') as f:
            with self.index_lock:
                pkl.dump(self.index, f, pkl.HIGHEST_PROTOCOL)
        pass

    def _add_item_to_index(self, index_var, key, value):
        # add a single item to the index
        with self.index_lock:
            try:
                self.index[index_var][key].append(value)
            except KeyError:
                self.index[index_var][key] = [value]
            pass

    def _add_doc_to_index(self, doc_id, doc, doc_txt=None, to_file=True,):
        # add a single document to the index file
        # doc_id is the row number of the record in self.metadata 
        # doc is the record in self.metadata (i.e. one row of the dataframe)
        for index_var in self.index_vars:
            if index_var=='keyword':
                if doc_txt is None:
                    with open(doc['local_path_txt'], 'r') as f:
                        doc_txt = f.read()
                tokens = self.tokenizer.tokenize(doc_txt)
                tokens = [t.upper() for t in tokens]
                counter = Counter(tokens)
                for token, count in counter.items():
                    self._add_item_to_index(index_var, token, (doc_id, count))        
        if to_file:
            self._save_index()

    def _download_doc(self, doc):
        # download a document from given url to designated local location
        local_path = doc['local_path_pdf']
        os.makedirs(os.path.split(local_path)[0], exist_ok=True)
        url = doc['url'].replace(' ', '%20')
        urlretrieve(url, local_path)            
        pass

    def _convert_doc(self, doc):
        # convert a pdf to txt and save in designated location
        pdf_path = doc['local_path_pdf']
        txt_path = doc['local_path_txt']
        os.makedirs(os.path.split(txt_path)[0], exist_ok=True)
        args = [pdf_path, '-o', txt_path]
        pdf2txt(args)
        pass


    def _write_doc_fname(self, doc):
        # produce the file name which the document will be known by locally.
        # `doc` variable must contain fields:  city, date, committee
        date = doc['date'].strftime('%Y-%m-%d')
        city = doc['city'].title().replace(' ', '-')
        committee = doc['committee'].title().replace(' ', '-')
        doc_type = doc['doc_type'].title().replace(' ', '-')
        return '{}_{}_{}_{}'.format(city, date, committee, doc_type)        


    def _parse_doc_fname(self, fname):
        # given a file name, extract the document properties
        fname = fname[:-4]
        city, date, committee, doc_type = fname.split('_')
        city = city.replace('-', ' ')
        committee = committee.replace('-', ' ')
        date = datetime.strptime(date, '%Y-%m-%d').date()
        doc_type = doc_type.replace('-', ' ')
        return city, date, committee, doc_type


    def _write_city_dir(self, doc):
        # return a file-structure friendly form of a city name
        return doc['city'].lower().replace(' ', '-')


    def _parse_city_dir(self, city_dir): 
        # get city name back from a file-structure friendly version
        return city_dir.replace('-', ' ').title()


    def _write_doc_paths(self, doc):
        doc_paths = {}
        for s in ['pdf', 'txt']:
            k = 'local_path_' + s
            doc_paths[k] = os.path.abspath(
                os.path.join(
                    self.document_dir,
                    self._write_city_dir(doc),
                    s,
                    '{}.{}'.format(self._write_doc_fname(doc), s)
                )
            ) 
        return doc_paths

    # def process_pdf_url(pdf_url, city):
    #     # city = df["City"]
    #     # pdf_url = df["Agendas"]
    #     if not isinstance(pdf_url, str):
    #         return ""
    #     citydir = os.path.join(data_dir, city)
    #     pdfdir = os.path.join(citydir, "pdf")
    #     txtdir = os.path.join(citydir, 'txt')
    #     pdfname = os.path.basename(pdf_url)
    #     local_pdf_path = os.path.join(pdfdir, pdfname)
    #     txtname = pdfname[:-4] + '.txt'
    #     txt_path = os.path.join(txtdir, txtname)
    #     if not os.path.exists(local_pdf_path):
    #         if not os.path.exists(citydir):
    #             os.mkdir(citydir)
    #         if not os.path.exists(pdfdir):
    #             os.mkdir(pdfdir)
            
    #     if not os.path.exists(txt_path):
    #         if not os.path.exists(txtdir):
    #             os.mkdir(txtdir)
    #         args = [local_pdf_path, '-o', txt_path]
    #         pdf2txt(args)
    #     with open(txt_path, 'r') as f:
    #         return f.read()


    # load data
    # example_data_path = '../data/meeting_database/example_meeting_database.csv'
    # datetime_cols = ['Date']
    # categorical_vars = ['Committee', 'City']
    # column_dtypes = {v: 'category' for v in categorical_vars}
    # data = pd.read_csv(example_data_path, parse_dates=datetime_cols, dtype=column_dtypes)

    # get range of values of each column
    
        # metadata file (minimally) has columns:
        # city
        # committee
        # date
        # local_path_txt,
        # local_path_pdf
        # url

        # # traverse file structure
        # self.cities = []
        # self.files = []
        # with os.scandir(self.document_dir) as city_dirs:                                    
        #     for entry in city_dirs:                
        #         if entry.is_dir():                    
        #             self.cities.append(self._parse_city_dir(entry.name))
        #             if os.path.exists(os.path.join(entry.path, 'pdf')):
        #                 files = os.listdir(os.path.join(entry.path, 'pdf'))                        
        #                 self.files.extend(files)
        # import pdb;pdb.set_trace()

        # # build text files and save metadata
        # for fi in self.files:     
        #     city, date, committee, doc_type = self._parse_doc_fname(os.path.split(fi)[0])            
        #     d = {
        #         'city': city,
        #         'date': date,
        #         'committee': committee,
        #         'doc_type': doc_type,
        #         'local_path_pdf': fi,
        #         'local_path_txt': None
        #     }
        #     metadata = pd.DataFrame(d, columns=self.metadata_vars)
        # else:   



    # def add_doc_from_url(
    #     self,
    #     city,
    #     committee,
    #     doc_type,
    #     date,
    #     url,
    #     addl_fields=None
    #     ):
    #     # downloads a document from URL to appropriate local path
    #     # runs pdfminer and gets txt version
    #     # updates document list and index accordingly
    #     # addl_fields contains any additional information to include with the record

    #     doc = {
    #         'city': city,
    #         'committee': committee,
    #         'date': date,
    #         'doc_type': doc_type,
    #         'url': url,
    #         'local_path_pdf': None,
    #         'local_path_txt': None,
    #     }
    #     doc.update(addl_fields)

    #     # calculate local paths


    #     self._add_doc_to_metadata(doc)
    #     self._add_doc_to_index(doc)

    #     pass

    """
    Interface for reading from document database.
    """
    # def _load_metadata(
    #     self,
    #     force_build_metadata=True
    #     ):
    #     self.metadata = self.build_metadata(**kwargs)
    #     pass

    # def _load_index(
    #     self,
    #     force_build_index=True
    #     ):
    #     self.index = self.build_index(**kwargs)
    #     pass
