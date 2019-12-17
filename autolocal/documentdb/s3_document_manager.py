import os
from datetime import datetime

import pandas as pd
import numpy as np
from urllib.request import urlretrieve
from tqdm import tqdm

import boto3
from boto3.dynamodb.conditions import Key, Attr
import botocore

from autolocal import AUTOLOCAL_HOME
from autolocal.documentdb import pdf2txt, DocumentManager
from autolocal.aws import aws_config
from autolocal.parser.nlp import Vectorizer

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
        s3_bucket_name=aws_config.s3_document_bucket_name,
        db_name=aws_config.db_document_table_name,
        region_name=aws_config.region_name,
        document_base_dir='docs',
        local_tmp_dir=os.path.join(AUTOLOCAL_HOME, 'data', 'scraping', 'tmp'),
        tokenizer_args={},
        ):

        # store arguments
        self.s3_bucket_name = s3_bucket_name
        self.document_base_dir = 'docs'    
        self.local_tmp_dir = os.path.expanduser(local_tmp_dir)
        if not os.path.exists(self.local_tmp_dir):
            os.mkdir(self.local_tmp_dir) 

        self.vectorizer = Vectorizer()           

        # init resources
        self.table = boto3.resource(
            'dynamodb',
            region_name=region_name
            ).Table(db_name)
        self.s3 = boto3.resource(
            's3',
            region_name=region_name
            )
        self.s3_client = boto3.client(
            's3',
            region_name=region_name
            )

        # load metadata from file if it exists
        self.metadata_vars = METADATA_VARS

        pass

    """
    "Public" methods for reading and writing info from documents
    """

    def _get_tmp_path(self, doc, ext):
        return os.path.join(self.local_tmp_dir, '{}.{}'.format(self._get_doc_id(doc), ext))

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

    def _get_doc_paths(self, doc, formats=['pdf', 'txt', 'pkl']):
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


    def _download_doc(self, doc, doc_paths):
        # download a document from given url to designated local location
        try:
            self._get_doc_id(doc)
            tmp_path_pdf = self._get_tmp_path(doc, 'pdf')
            if os.path.exists(tmp_path_pdf):
                os.remove(tmp_path_pdf)
            s3_path_pdf = doc_paths['local_path_pdf']
            url = doc['url']
        except KeyError:
            print('warning: could not load path(s): {}'.format(doc['doc_id']))
            return doc
        if self._s3_object_exists(s3_path_pdf):
            print('s3: object already exists: {}'.format(s3_path_pdf))
            return doc
        else:        
            doc['download_timestamp'] = datetime.utcnow().isoformat()
            self._retrieve_url(url, tmp_path_pdf)            
            self._save_doc_to_s3(tmp_path_pdf, s3_path_pdf)
            os.remove(tmp_path_pdf)            
        return doc

    def _convert_doc(self, doc, doc_paths):
        # convert a pdf to txt and save in designated location
        if not doc['doc_format']=='pdf':
            print('warning: document format is not PDF:'.format(doc['doc_id']))
            return
        # get paths
        try:
            tmp_path_pdf = self._get_tmp_path(doc, 'pdf')
            tmp_path_txt = self._get_tmp_path(doc, 'txt')
            if os.path.exists(tmp_path_txt):
                os.remove(tmp_path_txt)
            s3_path_txt = doc_paths['local_path_txt']
        except KeyError:
            print('warning: could not load path(s): {}'.format(doc['doc_id']))
            return
        # check to see if txt already exists
        if self._s3_object_exists(s3_path_txt):
            print('s3: object already exists: {}'.format(s3_path_txt))
            return                
        # convert pdf
        try:
            s3_path_pdf = doc['local_path_pdf']
            self._load_doc_from_s3(s3_path_pdf, tmp_path_pdf)
            args = [tmp_path_pdf, '-o', tmp_path_txt]
            pdf2txt(args)
            if os.path.exists(tmp_path_pdf):
                os.remove(tmp_path_pdf)
        except Exception as e:
            print('warning: was not able to convert PDF: {}'.format(doc['doc_id']))
            print(e)
            return
        # copy to S3        
        self._save_doc_to_s3(tmp_path_txt, s3_path_txt)        
        if os.path.exists(tmp_path_txt):
            os.remove(tmp_path_txt)
        if os.path.exists(tmp_path_pdf):
            os.remove(tmp_path_pdf)
        return

    def get_doc_text(self, doc):
      if 'local_path_txt' in doc:
        s3_path_txt = doc['local_path_txt']
        autolocal_docs_bucket = self.s3.Bucket(self.s3_bucket_name)
        doc_string = autolocal_docs_bucket.Object(s3_path_txt).get()['Body'].read()
        # clear difficult characters
        doc_string = doc_string.decode("ascii", "ignore")
        return doc_string

    def _add_vectors(self, doc, doc_paths):
      s3_txt_path = doc_paths['local_path_txt']
      s3_pkl_path = doc_paths['local_path_pkl']
      tmp_pkl_path = self._get_tmp_path(doc, 'pkl')

      doc_string = self.get_doc_text(doc)
      if doc_string:
        print("vectorizing doc")
        vectors_data = self.vectorizer.vectorize(doc_string)
        pickle.dump(data_to_write, open(tmp_pkl_path, 'wb'))
        print("uploading doc")
        self.s3.meta.client.upload_file(tmp_pkl_path, self.s3_bucket_name, s3_pkl_path)
      if os.path.exists(tmp_pkl_path):
        os.remove(tmp_pkl_path)

    def get_doc_vectors(self, doc):
      # add document vectors if we don't already have them
      if not 'local_path_pkl' in doc:
        self.add_doc(doc)
      s3_path = doc['local_path_pkl']
      tmp_path = self._get_tmp_path(doc, 'pkl')
      self._load_doc_from_s3(s3_path, tmp_path)
      vector_data = pickle.load(open(tmp_path, 'rb'))
      if os.path.exists(tmp_pkl_path):
        os.remove(tmp_pkl_path)
      return vector_data

    def get_doc_by_id(self, doc_id):
      matching_docs = self._query_db_by_doc_id(doc_id)
      if len(matching_docs) == 0:
        print("no documents on s3 matching {}".format(doc_id))
        return None
      else:
        if len(matching_docs) > 1:
          print("more than one document on s3 matches {}. returning the first.".format(doc_id))
        return matching_docs.pop()

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

        # get local paths to document
        doc_paths = self._get_doc_paths(doc)
        #doc.update(doc_paths)

        if not self._s3_object_exists(doc_paths['local_path_pdf']):
          # download doc from url
          doc = self._download_doc(doc, doc_paths)
          doc['local_path_pdf'] = doc_paths['local_path_pdf']
            
        if not self._s3_object_exists(doc_paths['local_path_txt']):
          # convert to txt
          self._convert_doc(doc, doc_paths)
          doc['local_path_txt'] = doc_paths['local_path_txt']

        if not self._s3_object_exists(doc_paths['local_path_pkl']):
          self._add_vectors(doc, doc_paths)
          doc['local_path_pkl'] = doc_paths['local_path_pkl']

        # add to metadata and index
        if not self._query_db_by_doc_id(doc_id):
          self._add_doc_to_db(doc, batch)
        
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
        with self.table.batch_writer(overwrite_by_pkeys=['doc_id']) as batch:
            for _, row in tqdm(docs.iterrows()):
                self.add_doc(row, batch=batch)
            pass


