import json
import re

import boto3
from boto3.dynamodb.conditions import Key, Attr
import boto3

from datetime import datetime
from hashlib import sha3_224

from autolocal.aws import aws_config
from .emails import ConfirmSubscriptionEmail
from .emails import ConfirmUnsubscribeEmail
from .emails import RecommendationEmail

email_re = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')

UNSUBSCRIBED = 'unsubscribed'
SUBSCRIBED = 'subscribed'
PENDING = 'pending'
SUBSCRIBE_FORM_KEYS = ['email_address', 'keywords', 'municipalities']


class MailerEvent(object):
    def __init__(self, event):
        # get event info
        self.event_timestamp = datetime.utcnow().isoformat()
        self.event_data = event

        # get dynamodb table
        self.queries = boto3.resource(
            'dynamodb',
            region_name=aws_config.region_name,
            ).Table(aws_config.db_query_table_name)
        self.recommendations = boto3.resource(
            'dynamodb',
            region_name=aws_config.region_name,
            ).Table(aws_config.db_recommendation_table_name)

        # any other init functions
        self._custom_init()        

    def _custom_init(self):
        pass

    def _scrub_data(self, key):
        # scrub inputs of different types    
        data = self.event_data[key]
        if key=='email_address':
            try:
                data = email_re.findall(data)[0]
            except:
                raise ValueError('Not a valid email address: {}'.format(data))
            return data
        elif key=='municipalities':
            try:
                for elm in data:
                    assert(elm in aws_config.supported_municipalities)
            except:
                raise ValueError('Not a valid list of municipalities: {}'.format(data))
            return data
        elif key=='query_id' or key=='qid':
            try:
                data = str(data)[:56]
            except:
                raise ValueError('Not a valid query_id: {}'.format(data))
            return data
        else:
            return data

    """
    Helper functions to interface with DynamoDB
    """

    def _compute_qid(self, data):
        v_li = []
        for k in ['email_address', 'keywords', 'municipalities']:
            if isinstance(data[k], list):
                v_li.append(k+':'+','.join(data[k]))
            elif isinstance(data[k], str):
                v_li.append(k+':'+data[k])
        s = ';'.join(v_li)    
        query_id = sha3_224(s.encode('utf-8')).hexdigest()
        return query_id            

    def _get_query_by_id(self, query_id, **kwargs):
        return self.queries.get_item(Key={'id':query_id}, **kwargs)['Item']

    def _put_query(self, query, **kwargs):
        self.queries.put_item(Item=query, **kwargs)
        pass

    def _update_query_by_qid(self, qid, new_data):
        query = self._get_query_by_id(qid)
        query.update(new_data)
        self._put_query(query)
        pass

    def _get_qids_by_attr_value(self, attribute, value):
        # returns a list of all the query ids where query[attribute]==value
        fe = Key(attribute).eq(value)
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
        return [q['id'] for q in query_ids]      

    def _timestamp_subscription_status(self, new_status):
        metadata = {
            'subscription_status_last_updated_timestamp': self.event_timestamp,
            'subscription_status': new_status,
        }
        return metadata
    
    def _update_subscription_status_by_qid(self, qid, new_status):
        metadata = self._timestamp_subscription_status(new_status)
        self._update_query_by_qid(qid, metadata)
        pass

    def _update_subscription_status_by_email_address(self, email_address, new_status):
        query_ids = self._get_qids_by_attr_value('email_address', email_address)        
        for qid in query_ids:                        
            self._update_subscription_status_by_qid(qid, new_status)
        pass


class SubscribeEvent(MailerEvent):
    """
    Functions related to a subscription event

    """
    def _custom_init(self):
        # scrub inputs and create unique query ID
        self.form_data = {k: self._scrub_data(k) for k in SUBSCRIBE_FORM_KEYS}
        self.qid = self._compute_qid(self.form_data)
        self.form_data['id'] = self.qid
        self.email_address = self.form_data['email_address']
        pass

    def write_record_to_db(self):
        timestamps = {
            'subscribed_timestamp': self.event_timestamp,
            'most_recent_digest_timestamp': 'none',
        }
        subscription_status = self._timestamp_subscription_status(PENDING)
        self.form_data.update(timestamps)
        self.form_data.update(subscription_status)
        self._put_query(self.form_data)
        pass        

    def send_confirmation_email(self):
        m = ConfirmSubscriptionEmail(query=self.form_data)
        m.send()
        pass


class ConfirmSubscriptionEvent(MailerEvent):
    """
    Functions related to a confirm subscription event
    """
    def _custom_init(self):                
        self.query_id = self._scrub_data('qid')
        self.query = self._get_query_by_id(self.query_id)
        self.email_address = self.query['email_address']
        pass

    def subscribe_query(self):
        # updates subscription_status to 'subscribed'
        self._update_subscription_status_by_qid(self.query_id, SUBSCRIBED)
        pass


class UnsubscribeEvent(MailerEvent):
    """
    Functions related to an unsubscribe event
    """       
    def _custom_init(self):
        self.email_address = self._scrub_data('email_address')

    def get_query_ids(self):
        # scan signup table to get queries that contain email                
        qids = self._get_qids_by_attr_value('email_address', self.email_address)
        return qids

    def send_confirmation_email(self):
        m = ConfirmUnsubscribeEmail(email_address=self.email_address)
        m.send()
        pass

class ConfirmUnsubscribeEvent(MailerEvent):
    """
    Functions related to a confirm subscription event
    """    
    def _custom_init(self):                     
        self.email_address = self._scrub_data('email_address')
        pass

    def unsubscribe_queries(self):
        self._update_subscription_status_by_email_address(self.email_address, UNSUBSCRIBED)
        pass

class RecommendationEvent(MailerEvent):
    """
    Functions related to a recommendations event
    """    

    def _custom_init(self):
        boto3.resource('dynamodb')
        deserializer = boto3.dynamodb.types.TypeDeserializer()
        self.new_records = []
        for r in self.event_data['Records']:
            if r['eventName']=='INSERT':
                d = {k: deserializer.deserialize(v) for k,v in r['dynamodb']['NewImage'].items()}
                self.new_records.append(d)
        pass

    def send_recommendation_emails(self):
        # m = RecommendationEmail(recommendation=self.recommendation)        # m.send_email()
        for record in self.new_records:
            # send_test_email('chstock@stanford.edu', recommendation)
            m = RecommendationEmail(record=record)
            m.send()
        pass



