import json
import re

import boto3
from boto3.dynamodb.conditions import Key, Attr

from datetime import datetime
from hashlib import sha3_224

from .email_formats import ConfirmSubscriptionEmail


SUPPORTED_MUNICIPALITIES = [
    "Alameda",
    "Burlingame",
    "Cupertino",
    "Hayward",
    "Hercules",
    "Metropolitan Transportation Commission",
    "Mountain View",
    "Oakland",
    "San Francisco",
    "San Jose",
    "San Leandro",
    "San Mateo County",
    "Santa Clara",
    "South San Francisco",
    "Stockton",
    "Sunnyvale",
]

email_re = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')

def Event(object):
    def __init__(self, event):
        # get event info
        self.event_timestamp = datetime.utcnow().isoformat()
        self.event_data = json.loads(event['body'])

        # get dynamodb table
        self.queries = boto3.resource('dynamodb', region_name='us-west-1').Table('autolocal-user-queries')
        self.recommendations = boto3.resource('dynamodb', region_name='us-west-1').Table('autolocal-recommendations')

        # any other init functions
        self._custom_init()        

    def _custom_init(self):
        pass

    def _scrub_data(self, key):
        # scrub inputs of different types    
        data = self.event_data[key]
        if key=='email_address':
            try:
                scrubbed_data = email_re.findall(data)[0]
            except:
                raise ValueError('Not a valid email address: {}'.format(data))
            return scrubbed_data
        elif key=='municipalities':
            try:
                for elm in data:
                    assert(elm in SUPPORTED_MUNICIPALITIES)
            except:
                raise ValueError('Not a valid list of municipalities: {}'.format(data))
            return data
        else:
            return data
    

def SubscribeEvent(Event):
    """
    Functions related to a subscription event

    """
    def _custom_init(self):
        self.form_keys = ['email_address', 'keywords', 'municipalities']
        record = {k: self._scrub_data(k) for k in self.form_keys}
        record['id']: self._get_query_id(record)
        metadata = {
            'subscribed_timestamp': self.event_timestamp,
            'subscription_status_last_updated_timestamp': self.event_timestamp
            'subscription_status': 'pending',
            'most_recent_digest_timestamp': 'none',
        }
        record.update(metadata)
        self.record = record

    def _get_query_id(self, data):
        v_li = []
        for k in ['email_address', 'keywords', 'municipalities']:
            if isinstance(data[k], list):
                v_li.append(k+':'+','.join(data[k]))
            elif isinstance(data[k], str):
                v_li.append(k+':'+data[k])
        s = ';'.join(v_li)    
        query_id = sha3_224(s.encode('utf-8')).hexdigest()
        return query_id

    def write_record_to_db(self):
        self.queries.put_item(Item=self.record)
        pass

    def send_confirmation_email(self,):
        m = ConfirmSubscriptionEmail(self.record)
        m.send()
        pass


def ConfirmSubscriptionEvent(Event):
    """
    Functions related to a confirm subscription event
    """    
    def _custom_init(self):
        #TODO
        pass

    def update_db(self):
        # updates subscription_status to 'subscribed'
        #TODO
        # 
        pass


def UnsubscribeEvent(Event):
    """
    Functions related to an unsubscribe event
    """       
    def _custom_init(self):
        self.email_address = self._scrub_data('email_address')

    def get_query_ids(self, email_address):
        # scan signup table to get queries that contain email        
        fe = Key('email_address').eq(self.email_address)
        pe = 'id'
        response = self.queries.scan(
            FilterExpression=fe,
            ProjectionExpression=pe,
            )
        query_ids = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=fe,
                ProjectionExpression=pe,
                ExclusiveStartKey=response['LastEvaluatedKey']
                )
            query_ids.extend(response['Items'])
        return query_ids

def unsubscribe_queries(self, query_ids):
    metadata = {
        'subscription_status_last_updated_timestamp': self.event_timestamp
        'subscription_status': 'unsubscribed',
    }
    for qid in query_ids:
        query = self.queries.get_item(Key={'id':qid})['Item']
        query.update(metadata)
        self.queries.put_item(Item=query)
    pass

            
