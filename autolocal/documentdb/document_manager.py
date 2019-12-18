import os
from datetime import datetime
import string
import pandas as pd

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

    def _get_doc_id(self, doc):
        # produce the file name which the document will be known by locally.
        # `doc` variable must contain fields:  city, date, committee
        transform = lambda s: s.title().translate(str.maketrans('', '', string.punctuation)).replace(' ', '-')
        date = pd.to_datetime(doc['date']).strftime('%Y-%m-%d')
        city = transform(doc['city'])
        committee = transform(doc['committee'])
        if 'meeting_type' in doc and isinstance(doc['meeting_type'], str):
            meeting_type = transform(doc['meeting_type'])
        else:
            meeting_type = None
        doc_type = transform(doc['doc_type'])
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
