import os
from collections import Counter
from datetime import datetime
import pickle as pkl
from time import time
from datetime import datetime

import pandas as pd
import numpy as np
from urllib.request import urlretrieve
from tqdm import tqdm

from autolocal.pdf2txt import pdf2txt
# from autolocal import nlp
from autolocal.databases import DocumentManager

import boto3
from boto3.dynamodb.conditions import Key, Attr
import botocore

METADATA_VARS = [
    'city',
    'committee',
    'date',
    'doc_type',
    'meeting_type',
    'url',
    'local_path_pdf',
    'local_path_txt',
    'doc_format',
    'download_timestamp'
]

class S3DocumentManager(DocumentManager):
    """
    Class to manage repository of PDF (and TXT) documents        
    """    
    def __init__(
        self,
        s3_bucket_name='autolocal-documents',
        db_name='autolocal-documents',
        document_base_dir='docs',
        local_tmp_dir='~/autolocal/data/scraping/tmp',
        tokenizer_args={},
        ):

        # store arguments
        self.s3_bucket_name = s3_bucket_name
        self.document_base_dir = 'docs'    
        self.local_tmp_dir = os.path.expanduser(local_tmp_dir)
        if not os.path.exists(self.local_tmp_dir):
            os.mkdir(self.local_tmp_dir)
        self.tmp_paths = {
            ext: os.path.join(self.local_tmp_dir, 'doc.{}'.format(ext))
                for ext in ['txt', 'pdf']
            }

        # init resources
        self.table = boto3.resource('dynamodb').Table(db_name)
        self.s3 = boto3.resource('s3')
        self.s3_client = boto3.client('s3')

        # load metadata from file if it exists
        self.metadata_vars = METADATA_VARS

        pass

    """
    "Public" methods for reading and writing info from documents
    """

    def _save_doc_to_s3(self, local_path, s3_path):
        return self.s3_client.upload_file(local_path, self.s3_bucket_name, s3_path)

    def _load_doc_from_s3(self, s3_path, local_path):
        return self.s3_client.download_file(self.s3_bucket_name, s3_path, local_path)

    def _s3_object_exists(self, s3_path):
        try:
            self.s3.Object(self.s3_bucket_name, s3_path).load()
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                raise e

    def _add_doc_to_db(self, doc, batch=None):        
        doc = dict(doc)
        item = {}
        for k,v in doc.items():
            if isinstance(v, str):
                item[k] = v
            else:
                pass
        if batch is not None:
            return batch.put_item(Item=item)
        else:
            return self.table.put_item(Item=item)

    def _query_db_by_doc_id(self, doc_id):
        return self.table.query(KeyConditionExpression=Key('doc_id').eq(doc_id))['Items']

    def _get_doc_paths(self, doc, formats=['pdf', 'txt']):
        doc_paths = {'local_path_' + s: '' for s in formats}
        if doc['url']:
            for s in formats:
                k = 'local_path_' + s
                doc_paths[k] = os.path.join(
                    self.document_base_dir,
                    self._lower(doc['city']),
                    '{}.{}'.format(self._get_doc_id(doc), s)
                )
        return doc_paths

    def _retrieve_url(self, url, local_path):
        try:
            urlretrieve(url.replace(' ', '%20'), local_path)
        except:
            print('warning: could not retrieve url: {}'.format(url))


    def _download_doc(self, doc):
        # download a document from given url to designated local location
        try:
            tmp_path_pdf = self.tmp_paths['pdf']
            s3_path_pdf = doc['local_path_pdf']
            url = doc['url']
        except KeyError:
            print('warning: could not load path(s): {}'.format(doc['doc_id']))
            return doc
        if self._s3_object_exists(s3_path_pdf):
            print('object already exists: {}'.format(s3_path_pdf))
            return doc
        else:        
            self._retrieve_url(url, tmp_path_pdf)
            self._save_doc_to_s3(tmp_path_pdf, s3_path_pdf)
            doc['download_timestamp'] = datetime.now().isoformat()
        return doc

    def _convert_doc(self, doc):
        # convert a pdf to txt and save in designated location
        if not doc['doc_format']=='pdf':
            print('warning: document format is not PDF:'.format(doc['doc_id']))
            return
        # get paths
        try:
            tmp_path_pdf = self.tmp_paths['pdf']
            tmp_path_txt = self.tmp_paths['txt']
            s3_path_txt = doc['local_path_txt']
        except KeyError:
            print('warning: could not load path(s): {}'.format(doc['doc_id']))
            return
        # check to see if txt already exists
        if self._s3_object_exists(s3_path_txt):
            print('object already exists: {}'.format(s3_path_txt))
            return                
        # convert pdf
        try:
            args = [tmp_path_pdf, '-o', tmp_path_txt]
            pdf2txt(args)
        except:
            print('warning: was not able to convert PDF: {}'.format(doc['doc_id']))
            return
        # copy to S3        
        self._save_doc_to_s3(tmp_path_txt, s3_path_txt)        
        return

    def add_doc(
        self,
        new_doc,     
        batch=None
        ):
        # add a document to the database.
        # new_doc must be a dict (or row of dataframe) with fields:
        # city, committee, doc_type, date,
        # and optionally, if you want to download and index the document, 
        # url 

        new_doc = {k: str(v) for k, v in new_doc.items()}        
        doc = {k: np.nan for k in self.metadata_vars}
        doc.update(new_doc)

        # do not add document if no url
        if not isinstance(doc['url'], str):
            return

        # don't add the document if we already have it
        doc_id = self._get_doc_id(doc)
        doc['doc_id'] = doc_id
        if self._query_db_by_doc_id(doc_id):
            print('document already in database: {}'.format(doc_id))
            return

        # get local paths to document        
        doc_paths = self._get_doc_paths(doc)
        doc.update(doc_paths)

        # download doc from url
        doc = self._download_doc(doc)          
            
        # convert to txt        
        self._convert_doc(doc)

        # add to metadata and index
        self._add_doc_to_db(doc, batch)
        
        # done
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
        
        docs = pd.read_csv(csv_path, index_col=0)
        with self.table.batch_writer(overwrite_by_pkeys=['partition_key', 'sort_key']) as batch:
            for _, row in tqdm(docs.iterrows()):
                self.add_doc(row, batch=batch)
            pass


