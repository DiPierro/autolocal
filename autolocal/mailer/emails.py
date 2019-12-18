from .mailers import SESMailer
from urllib.parse import urlencode
from autolocal.aws import aws_config
from datetime import datetime
import re

import boto3
from boto3.dynamodb.conditions import Key, Attr

from autolocal.aws import aws_config

class Email(object):

    def __init__(
        self,
        recipient_address=None,
        subject=None,        
        body_html=None,
        body_text=None,
        sender_name=None,
        sender_address=None,   
        **kwargs     
        ):
        
        self.recipient_address = recipient_address
        self.subject = subject        
        self.body_html = body_html
        self.body_text = body_text
        self.sender_name = sender_name
        self.sender_address = sender_address

        self._custom_init(**kwargs)

    def _custom_init(self, **kwargs):  
        pass

    def add_unsubscribe_link(self):
        pass

    def send(
        self,
        sender='SES',
        sender_args={}
        ):

        # initialize engine
        if sender=='SES':
            engine = SESMailer(**sender_args)
        else:
            raise ValueError('Sender not known: {}'.format(sender))
        
        # send email
        message = engine.send_email(self)
        return message


class ConfirmSubscriptionEmail(Email):

    def _custom_init(self, **kwargs):
        
        # get information from query
        query = kwargs['query']
        api_url = aws_config.api_urls['confirmSubscription']
        get_params = urlencode({'qid': query['id']})
        url = '{}?{}'.format(api_url, get_params)
        keywords = ', '.join(query['keywords'])
        municipalities = ', '.join(query['municipalities'])

        # specify email contents
        self.recipient_address = query['email_address']
        self.subject = 'Agenda Watch: Please Confirm Subscription'
        self.body_html = """
        <html>
        <head></head>
        <body>
        <h1>Please confirm your subscription to Agenda Watch</h1>
        <h3>We received a request to subscribe this email address to periodic, personalized email alerts.
        To confirm your subscription, please click 
        <a href={}>here</a>.
        </h3>
        <p>Keywords: {}</p>
        <p>Municipalities: {}</p>
        <p>If you did not sign up for emails from Agenda Watch, simply ignore this message.
        Feel free to email us with any questions at 
        <a href='mailto:{}'>{}</a>.
        </p>
        </body>
        </html>
        """.format(
            url,
            keywords,
            municipalities,
            aws_config.email_addresses['contact'],
            aws_config.email_addresses['contact'],
            )
        self.body_text = """
        Please confirm your subscription to Agenda Watch\r\n
        We received a request to subscribe this email address to periodic, personalized email alerts.
        To confirm your subscription, please visit the following URL:\r\n        
        {}\r\n
        Keywords: {}\r\n
        Municipalities: {}\r\n        
        If you did not sign up for emails from Agenda Watch, simply ignore this message.
        Feel free to email us with any questions at {}.
        """.format(
            url,
            keywords,
            municipalities,
            aws_config.email_addresses['contact'],
            )
        self.sender_name = aws_config.email_addresses['sender_name']
        self.sender_address = aws_config.email_addresses['list_manager']


class ConfirmUnsubscribeEmail(Email):

    def _custom_init(self, **kwargs):
        
        # get information from query
        email_address = kwargs['email_address']        
        api_url = aws_config.api_urls['confirmUnsubscribe']
        get_params = urlencode({'email_address': email_address})
        url = '{}?{}'.format(api_url, get_params)

        # specify email contents
        self.recipient_address = email_address
        self.subject = 'Agenda Watch: Please Confirm Unsubscribe Request'
        self.body_html = """
        <html>
        <head></head>
        <body>
        <h1>Please confirm your unsubscribe request</h1>
        <h3>We received a request to unsubscribe this email address from all Agenda Watch messages.
        To confirm, please click 
        <a href='{}'>here</a>.
        </h3>
        <p>If you did not attempt to unsubscribe from Agenda Watch, simply ignore this message.
        Feel free to email us with any questions at 
        <a href='mailto:{}'>{}</a>.
        </p>
        </body>
        </html>
        """.format(
            url,
            aws_config.email_addresses['contact'],
            aws_config.email_addresses['contact']
            )
        self.body_text = """
        Please confirm your unsubscribe request\r\n
        We received a request to unsubscribe this email address from all Agenda Watch messages.        
        To confirm, please visit the following URL:\r\n        
        {}\r\n
        If you did not attempt to unsubscribe from Agenda Watch, simply ignore this message.
        Feel free to email us with any questions at {}.
        """.format(
            url,
            aws_config.email_addresses['contact'],
            )
        self.sender_name = aws_config.email_addresses['sender_name']
        self.sender_address = aws_config.email_addresses['list_manager']

class UnsubscribeEmail(Email):

    def _custom_init(self, **kwargs):
        
        # get information from query
        email_address = kwargs['email_address']
        
        # specify email contents
        self.recipient_address = email_address
        self.subject = 'Agenda Watch: You are unsubscribed'
        self.body_html = """
        <html>
        <head></head>
        <body>
        <h1>You are now unsubscribed from Agenda Watch</h1>
        <h3>We won't email {} again.</h3>
        <p>If you did not mean to unsubscribe, or if you change your mind, sign up for a new alert at
        <a href='http://agendawatch.org'>agendawatch.org</a>.
        Feel free to email us with any questions at 
        <a href="mailto:{}:">{}</a>.
        </p>
        </body>
        </html>
        """.format(
            email_address,
            aws_config.email_addresses['contact'],
            aws_config.email_addresses['contact']
            )
        self.body_text = """
        You are now unsubscribed from Agenda Watch\r\n
        We won't email {} again.\r\n
        If you did not mean to unsubscribe, or if you change your mind, sign up for a new alert at agendawatch.org.
        Feel free to email us with any questions at {}.
        """.format(
            email_address,
            aws_config.email_addresses['contact'],
            )
        self.sender_name = aws_config.email_addresses['sender_name']
        self.sender_address = aws_config.email_addresses['list_manager']

class RecommendationEmail(Email):
    def _custom_init(self, **kwargs):
        # get information from recommendations
        record = kwargs['record']
        recommender_output = record['recommendations']
        query_id = record['query_id']
        recommendations = record['recommendations']


        query_data = self._get_query_data(query_id)
        email_address = query_data['email_address']
        keywords = query_data['keywords']
        municipalities = query_data['municipalities']        

        # specify email contents
        self.recipient_address = email_address
        self.subject = 'Agenda Watch: Your recommendations'
        self.body_html = """
            <html>
            <head>
              <link rel="stylesheet" href="http://agendawatch.org/css/main.css"/>
              <style>
              </style>
            </head>
            <body>
              <div id="wrapper">
                <div id="main">
                  <div class="container">
                    <section id="first">
                      <header class="major">
                        <h2>Your recommendations for {}</h2>

                        <h5>Keywords: {}</h5>

                        <h5>Municipalities: {}</h5>
                      </header>

                      {}

                    </div>
                  </section>

                  <section id="footer">
                    <div class="container">
                      <p>
                        If you would like to unsubscribe from Agenda Watch, please visit
                        <a href='http://agendawatch.org/unsubscribe'>agendawatch.org/unsubscribe</a>.
                        Feel free to email us with any questions at 
                        <a href="mailto:{}:">{}</a>.
                      </p>
                    </div>
                  </section>
                </div>
              </div>
            </body>
            </html>

        """.format(
            datetime.now().strftime("%B %d, %Y"),
            ", ".join(keywords),
            ", ".join(municipalities),
            self._format_recommendations(recommendations),
            aws_config.email_addresses['contact'],
            aws_config.email_addresses['contact']
            )
        self.body_text = self._html_to_txt(self.body_html)
        self.sender_name = aws_config.email_addresses['sender_name']
        self.sender_address = aws_config.email_addresses['agenda_bot']

    def _html_to_txt(self, body_html):
        # soup = BeautifulSoup(body_html)
        # return soup.text
        return re.sub(body_html, "<.*>", "")

    def _format_recommendation(self, recommendation):
        doc_id = recommendation['doc_id']
        text = recommendation['section_text']
        page = recommendation['start_page']
        doc = self._get_doc_data(doc_id)
        return """
            <header class="minor">
                <h2>{}</h2>
                <p> {}, {} </p>
            </header>
            <p>
             "...{}..." (page {})
            </p>
            <p><a href="{}">Link to original document</a></p>
        """.format(
                doc['committee'],
                doc['doc_type'],
                self._format_date(doc['date']),
                text,
                page,
                doc['url']
            )

    def _format_date(self, date_string):
        return datetime.strptime(date_string, '%Y-%m-%d').strftime("%B %d, %Y")

    def _format_recommendations(self, recommendations):
        return "\n\n".join([self._format_recommendation(r) for r in recommendations])

    def _get_query_data(self, query_id):
        table = boto3.resource(
            'dynamodb',
            region_name=aws_config.region_name,
            ).Table(aws_config.db_query_table_name)
        query = table.query(KeyConditionExpression=Key('id').eq(query_id))['Items'][0]
        return query

    def _get_doc_data(self, doc_id):
        table = boto3.resource(
            'dynamodb',
            region_name=aws_config.region_name,
            ).Table(aws_config.db_document_table_name)
        doc = table.query(KeyConditionExpression=Key('doc_id').eq(doc_id))['Items'][0]
        return doc




