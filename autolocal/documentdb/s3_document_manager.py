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
    'download_timestamp'
]

FORMATS = ['pdf', 'txt', 'pkl']

class S3DocumentManager(DocumentManager):
    """
    Class to manage repository of PDF (and TXT) documents        
    """    
    def __init__(
        self,
        s3_bucket_name=aws_config.s3_document_bucket_name,
        db_name=aws_config.db_document_table_name,
        region_name=aws_config.region_name,
        local_tmp_dir=os.path.join(AUTOLOCAL_HOME, 'data', 'scraping', 'tmp'),
        tokenizer_args={},
        doc_formats=FORMATS,
        metadata_vars=METADATA_VARS,
        ):

        # store arguments
        
        self.s3_bucket_name = s3_bucket_name
        self.doc_formats = doc_formats   
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
        self.metadata_vars = metadata_vars
        pass


    def _get_s3_path(self, doc, doc_format):                
        doc_path = os.path.join(
            doc_format,
            '{}.{}'.format(self._get_doc_id(doc), doc_format)
        )
        return doc_path

    def _get_tmp_path(self, doc, doc_format):
        tmp_path = os.path.join(
            self.local_tmp_dir,
            '{}.{}'.format(self._get_doc_id(doc), doc_format)
            )
        return tmp_path

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

    def _retrieve_url(self, url, local_path):
        try:
            urlretrieve(url.replace(' ', '%20'), local_path)
        except:
            print('warning: could not retrieve url: {}'.format(url))

    def _create_doc(self, new_doc):
        # initialize empty document
        doc = {k: np.nan for k in self.metadata_vars}        
        # add new data
        new_doc = {k: str(v) for k, v in new_doc.items()}        
        doc.update(new_doc)        
        # add doc id, now we're done
        doc['doc_id'] = self._get_doc_id(doc)        
        return doc

    def _download_doc(self, doc):
        # download a document from given url to designated local location
        try:
            self._get_doc_id(doc)
            tmp_path_pdf = self._get_tmp_path(doc, 'pdf')
            if os.path.exists(tmp_path_pdf):
                os.remove(tmp_path_pdf)
            s3_path_pdf = self._get_s3_path(doc, 'pdf')
            url = doc['url']
        except KeyError:
            print('document manager: could not setup local path(s): {}'.format(doc['doc_id']))
            return doc
        try:
            doc['download_timestamp'] = datetime.utcnow().isoformat()
            self._retrieve_url(url, tmp_path_pdf)            
            self._save_doc_to_s3(tmp_path_pdf, s3_path_pdf)
        except:
            print('document manager: could not download and save document: {}'.format(doc['doc_id']))        
        return doc

    def _convert_doc(self, doc):
        try:
            tmp_path_pdf = self._get_tmp_path(doc, 'pdf')
            tmp_path_txt = self._get_tmp_path(doc, 'txt')
            if os.path.exists(tmp_path_txt):
                os.remove(tmp_path_txt)
            s3_path_txt = self._get_s3_path(doc, 'txt')
        except KeyError:
            print('document manager: could not setup local path(s): {}'.format(doc['doc_id']))
            
        try:
            s3_path_pdf = doc['local_path_pdf']
            self._load_doc_from_s3(s3_path_pdf, tmp_path_pdf)
            args = [tmp_path_pdf, '-o', tmp_path_txt]
            pdf2txt(args)
        except Exception as e:
            print('warning: was not able to convert PDF: {}'.format(doc['doc_id']))
            print(e)
            return
        # copy to S3        
        try:
            self._save_doc_to_s3(tmp_path_txt, s3_path_txt)        
        except:
            print('document manager: unable to save to s3: {}.txt'.format(doc['doc_id']))        
        return

    def _add_vectors(self, doc):
      s3_txt_path = self._get_s3_path(doc, 'txt')
      s3_pkl_path = self._get_s3_path(doc, 'pdf')
      tmp_pkl_path = self._get_tmp_path(doc, 'pkl')

      doc_string = self.get_doc_text(doc)
      if doc_string:
        print("vectorizing doc: {}".format(doc['doc_id']))
        vectors_data = self.vectorizer.vectorize(doc_string)
        pickle.dump(data_to_write, open(tmp_pkl_path, 'wb'))
        print("uploading doc: {}".format(doc['doc_id']))
        self.s3.meta.client.upload_file(tmp_pkl_path, self.s3_bucket_name, s3_pkl_path)

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

    """
    "Public" methods for reading and writing info from documents
    """

    def get_doc_text(self, doc):
        s3_path_txt = self._get_s3_path(doc, 'txt')
        autolocal_docs_bucket = self.s3.Bucket(self.s3_bucket_name)
        doc_string = autolocal_docs_bucket.Object(s3_path_txt).get()['Body'].read()
        # clear difficult characters
        doc_string = doc_string.decode("ascii", "ignore")
        return doc_string

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

        # create doc dict
        doc = self._create_doc(new_doc)

        # do not add document if no url
        try:
            assert(isinstance(doc['url'], str))
        except:
            print('document manager: no URL provided in document {}'.format(doc['doc_id']))
            return

        # try to add every type of document format in turn
        for doc_format in self.doc_formats:            
            # compute the "local path" (actually path on s3)
            local_path = self._get_s3_path(doc, doc_format)
            local_path_key = 'local_path_{}'.format(doc_format)
            try:                
                # don't proceed if this doc format already exists on S3
                if self._s3_object_exists(local_path):
                    doc[local_path_key] = local_path
                    continue

                # do the right thing with this doc format
                if doc_format=='pdf':
                    self._download_doc(doc)
                elif doc_format =='txt':
                    self._convert_doc(doc)                
                elif doc_format=='pkl':
                    self._add_vectors(doc)
                else:
                    raise NotImplementedError

                # if successful, add s3 path to record
                doc[local_path_key] = local_path
            except Exception as e:                
                # let us know if something doesn't work while adding a document
                print('document manager: unable to add {} format for {}'.format(doc_format, doc['doc_id']))
                print(e)
                break

        # clean up
        for ext in self.doc_formats:
            tmp_path = self._get_tmp_path(doc, ext)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # add record to metadata and index            
        self._add_doc_to_db(doc, batch)        
        
        # done
        print('dynamodb: added document: {}'.format(doc['doc_id']))

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


