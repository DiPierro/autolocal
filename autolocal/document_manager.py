import os
import pdf2txt
import os
from urllib.request import urlretrieve
import pandas as pd
from nlp import Tokenizer
import numpy as np
from collections import Counter
from datetime import datetime
import threading

INDEX_VARS = ['Keyword']


class DocumentManager(object):
    """
    Class to manage repository of PDF (and TXT) documents        
    """    
    def __init__(
        self,
        document_dir='../data/docs',
        index_dir='../data/index'
        metadata_path='../data/index/doc_list'
        index_path='../data/index/index.json'
        force_build_metadata=False,
        force_build_index=False,
        tokenizer_args={},
        index_vars=INDEX_VARS,
        ):

        # store arguments
        self.document_dir = document_dir
        self.index_dir = index_dir
        self.metadata_path = metadata_path
        self.index_path = index_path
        self.index_vars = index_vars

        # init tokenizer
        self.tokenizer = Tokenizer(**tokenizer_args)

        # init locks
        self.metadata_lock = threading.RLock()
        self.index_lock = threading.RLock()

        # load metadata from file if it exists
        self.load_metadata(force_build_metadata)

        # load index from file if it exists
        self.load_index(force_build_index)

        pass

    def _write_doc_fname(self, doc):
        # doc must contain fields:  city, date, committee
        date = doc['date'].strftime('%Y-%m-%d')
        city = doc['city'].title().replace(' ', '-')
        committee = doc['committee'].title().replace(' ', '-')
        doc_type = doc['doc_type'].capitalize()
        return '{}_{}_{}_'.format(city, date, committee, doc_type)        

    def _parse_doc_fname(self, fname):
        city, date, committee, doc_type = fname.split('_')
        city = city.replace('-', ' ')
        committee = committee.replace('-', ' ')
        date = datetime.strptime(date, '%Y-%m-%d').date()
        return city, date, committee, doc_type

    def _write_city_dir(self, city):
        return city.replace(' ', '-')

    def _parse_city_dir(self, city_dir):
        return city_dir.replace('-', ' ')       

    def get_metadata(self):
        with self.metadata_lock:
            return self.metadata

    """
    Interface for writing to document database.
    """

    # metadata functionality
    def load_metadata(
        self,
        force_build_metadata=False
        ):
        if not force_build_metadata:
            try:
                self.metadata
                return
            except:
                if os.path.exists(self.metadata_path):
                    with self.metadata_lock:
                        self.metadata = pd.read_csv(self.metadata_path)
                        return            
        with self.metadata_lock:
            self.metadata = self.build_metadata(**kwargs)
        return

    def build_metadata(
        self,
        ):
        # metadata file (minimally) has columns:
        # city
        # committee
        # date
        # local_path_txt,
        # local_path_pdf
        # url

        # traverse document directory        
        self.cities = []
        with os.scandir(self.document_dir) as city_dirs:
            for entry in city_dirs:
                if entry.is_dir():
                    self.cities.append(self._parse_city_dir(entry))

    def save_metadata(
        self,
        metadata
        ):
        with self.metadata_lock:
            self.metadata = metadata
            self.metadata.to_csv(self.metadata_path)
        pass

    # index info    
    def load_index(
        self,
        force_build_index,
        **kwargs,
        ):

        if not force_build_index:
            try:
                self.index
                return
            except:
                if os.path.exists(self.index_path):
                    with self.index_lock:
                        self.index = pd.read_csv(self.index_path)
                        return
        with self.index_lock:
            self.index = self.build_index(**kwargs)
            return

    def _add_item_to_index(
        self,
        index_var,
        key,
        value):
        # index is keyed by the search term, values are a 

        with self.index_lock:
            try:
                self.index[index_var][key].append(value)
            except KeyError:
                self.index[index_var][key] = [value]
            pass

    def build_index(
        self):
        # builds corpus-wide index from scratch (overwriting existing index)

        # build metadata
        self.load_metadata()

        # initialize index
        with self.index_lock:
            self.index = {v: dict() for v in self.index_vars}
        
        # scan through documents in metadata
        with self.metadata_lock:
            for doc_id, doc in self.metadata.iterrows():
                self._add_doc_to_index(doc_id, doc, save=False)

        # save index when done
        self.save_idex(index)

    def save_index(
        self,
        index):

        self.index = index
        # save self.index to self.index_path
        pass

    # functionality for adding documents
    def _add_doc_to_metadata(
        self
        ):

        # load metadata
        metadata = self.load_metadata()
        # add a single document to the metadata file
        
        self.metadata_path

        pass

    def _add_doc_to_index(
        self,
        doc_id,
        doc,
        save=True,
        doc_txt=None
        ):
        # add a single document to the index file
        # doc_id is the doc_id number in self.metadata where the document is stored
        # doc is the doc_id of self.metadata corresponding to the document
        for index_var in self.index_vars:
            if index_var=='Keyword':
                if doc_txt is None:
                    with open(doc['local_path_txt'], 'r') as f:
                        doc_txt = f.read()
                tokens = self.tokenizer.tokenize(doc_txt)
                counter = Counter(tokens)
                for token, count in counter:
                    self._add_item_to_index(index_var, t, (doc_id, count))        
        if save:
            self.save_index(index)

    def add_docs_from_csv(
        self,
        csv_path,
        pass_fields=None,
        ):
        # downloads documents specified in csv_path
        # csv must contain fields: city, date, committee, url
        
        self.add_doc_to_metadata()
        self.add_doc_to_index()
        pass

    def add_doc_from_url(
        self,
        city,
        date,
        url,
        addl_fields=None
        ):
        # downloads a document from URL to appropriate local path
        # runs pdfminer and gets txt version
        # updates document list and index accordingly
        # addl_fields contains any additional information to put into the record
        self.add_doc_to_metadata(city, date, url, addl_fields)

        pass

    """
    Interface for reading from document database.
    """
    # def load_metadata(
    #     self,
    #     force_build_metadata=True
    #     ):
    #     self.metadata = self.build_metadata(**kwargs)
    #     pass

    # def load_index(
    #     self,
    #     force_build_index=True
    #     ):
    #     self.index = self.build_index(**kwargs)
    #     pass

    def get_count_vector(
        self,
        index_var,
        key
        ):
        # for a given index_var and key, gets a list of (doc_id, count) pairs 
        # and converts to vector of counts with len of metadata

        # initialize vector with same length as metadata
        with self.metadata_lock:
            with self.index_lock:
                counts = np.zeros(len(self.metadata), dtype=int)

                # see if the key is in the index; if not, return zero vector
                try:            
                    values = self.index[index_var][key]
                except KeyError:            
                    return counts

                # if key is in index, return the vector of counts across documents
                for doc_id, count in values:
                    counts[doc_id] = count
                return counts
        

    def process_pdf_url(pdf_url, city):
        # city = df["City"]
        # pdf_url = df["Agendas"]
        if not isinstance(pdf_url, str):
            return ""
        citydir = os.path.join(data_dir, city)
        pdfdir = os.path.join(citydir, "pdf")
        txtdir = os.path.join(citydir, 'txt')
        pdfname = os.path.basename(pdf_url)
        local_pdf_path = os.path.join(pdfdir, pdfname)
        txtname = pdfname[:-4] + '.txt'
        txt_path = os.path.join(txtdir, txtname)
        if not os.path.exists(local_pdf_path):
            if not os.path.exists(citydir):
                os.mkdir(citydir)
            if not os.path.exists(pdfdir):
                os.mkdir(pdfdir)
            urlretrieve(pdf_url.replace(" ", "%20"), local_pdf_path)
        if not os.path.exists(txt_path):
            if not os.path.exists(txtdir):
                os.mkdir(txtdir)
            args = [local_pdf_path, '-o', txt_path]
            pdf2txt.main(args)
        with open(txt_path, 'r') as f:
            return f.read()


    # load data
    example_data_path = '../data/meeting_database/example_meeting_database.csv'
    datetime_cols = ['Date']
    categorical_vars = ['Committee', 'City']
    column_dtypes = {v: 'category' for v in categorical_vars}
    data = pd.read_csv(example_data_path, parse_dates=datetime_cols, dtype=column_dtypes)

    # get range of values of each column
    
    datetime_range = 
