import json
import re
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key, Attr

from autolocal.aws import aws_config
from autolocal.events import MailerEvent
from autolocal.emails import Email

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
        now = datetime.now().strftime("%B %d, %Y")

        # specify email contents
        self.recipient_address = list_if_str(email_address)
        self.subject = 'Agenda Watch: Your recommendations -- {}'.format(now)
        self.body_html = """
        <html style="border:0; font:inherit; font-size:100%; margin:0; padding:0; vertical-align:baseline; box-sizing:border-box" valign="baseline">
        <head>
          <style>
        @import url("https://fonts.googleapis.com/css?family=Lato:400,400italic,700,700italic|Source+Code+Pro:400");
        </style>


          </head>
        <body style='border:0; font:inherit; font-size:11pt; margin:0; padding:0; vertical-align:baseline; line-height:1.75em; -webkit-text-size-adjust:none; background:#fff; color:#888; font-family:"Lato", sans-serif; font-weight:400' valign="baseline">
          <div id="wrapper" style="border:0; font:inherit; font-size:100%; margin:0; padding:0; vertical-align:baseline; background:#fff; padding-right:0" valign="baseline">
            <div id="main" style="border:0; font:inherit; font-size:100%; margin:0; padding:0; vertical-align:baseline" valign="baseline">
              <div class="container" style="border:0; font:inherit; font-size:100%; margin:0 auto; padding:0; vertical-align:baseline; max-width:calc(100% - 4.5em); width:45em" valign="baseline" width="45em">
                <section id="first" style="border:0; font:inherit; font-size:100%; margin:0; padding:0; vertical-align:baseline; display:block" valign="baseline">
                  <header class="major" style="border:0; font:inherit; font-size:100%; margin:0; padding:0; vertical-align:baseline; display:block" valign="baseline">
                    <h2 style="border:0; font:inherit; font-size:3.5em; margin:0 0 0.5625em 0; padding:0; vertical-align:baseline; color:#4acaa8; font-weight:700; line-height:1.5em" valign="baseline">Your recommendations for {}</h2>

                    <h5 style="border:0; font:inherit; font-size:0.9em; margin:0 0 0.5625em 0; padding:0; vertical-align:baseline; color:#777; font-weight:700; line-height:1.5em" valign="baseline">Keywords: {}</h5>

                    <h5 style="border:0; font:inherit; font-size:0.9em; margin:0 0 0.5625em 0; padding:0; vertical-align:baseline; color:#777; font-weight:700; line-height:1.5em" valign="baseline">Municipalities: {}</h5>
                  </header>

                  {}

                </section></div>
              

              <section id="footer" style="border:0; font:inherit; font-size:100%; margin:0; padding:0; vertical-align:baseline; display:block; background:#fafafa; border-top:solid 6px #f4f4f4; color:#c0c0c0; overflow:hidden" valign="baseline">
                <div class="container" style="border:0; font:inherit; font-size:100%; margin:0 auto; padding:1em 0 1em 0; vertical-align:baseline; max-width:calc(100% - 4.5em); width:45em" valign="baseline" width="45em">
                  <p style="border:0; font:inherit; font-size:100%; margin:0 0 2.25em 0; padding:0; vertical-align:baseline" valign="baseline">
                    If you would like to unsubscribe from Agenda Watch, please visit
                    <a href="http://agendawatch.org/unsubscribe" style="border:0; font:inherit; font-size:100%; margin:0; padding:0; vertical-align:baseline; -moz-transition:color 0.2s ease-in-out, border-color 0.2s ease-in-out; -ms-transition:color 0.2s ease-in-out, border-color 0.2s ease-in-out; -webkit-transition:color 0.2s ease-in-out, border-color 0.2s ease-in-out; border-bottom:solid 1px #e4e4e4; color:inherit; text-decoration:none; transition:color 0.2s ease-in-out, border-color 0.2s ease-in-out" valign="baseline">agendawatch.org/unsubscribe</a>.
                    Feel free to email us with any questions at 
                    <a href="mailto:%7B%7D:" style="border:0; font:inherit; font-size:100%; margin:0; padding:0; vertical-align:baseline; -moz-transition:color 0.2s ease-in-out, border-color 0.2s ease-in-out; -ms-transition:color 0.2s ease-in-out, border-color 0.2s ease-in-out; -webkit-transition:color 0.2s ease-in-out, border-color 0.2s ease-in-out; border-bottom:solid 1px #e4e4e4; color:inherit; text-decoration:none; transition:color 0.2s ease-in-out, border-color 0.2s ease-in-out" valign="baseline">{}</a>.
                  </p>
                </div>
              </section>
            </div>
          </div>
        </body>
        </html>
        """.format(
            now,
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
        return re.sub("<.*>", "", body_html)

    def _format_recommendation(self, recommendation):
        doc_id = recommendation['doc_id']
        text = recommendation['section_text']
        page = recommendation['start_page']
        doc = self._get_doc_data(doc_id)
        return """
            <header class="minor">
                <h2>{} {}</h2>
                <p> {}, {} </p>
            </header>
            <p>
             "...{}..." (page {})
            </p>
            <p><a href="{}">Link to original document</a></p>
        """.format(
                doc['city'],
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

def lambda_handler_send_recommendation(aws_event, context):
    try:
        event = RecommendationEvent(aws_event)
    except Exception as e:
        return {
                'statusCode': 400,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        } 
    try:
        event.send_recommendation_emails()
    except Exception as e:
        return {
                'statusCode': 500,
                'body': json.dumps(
                    'Error while attempting to send recommendation emails: {}.'.format(e)
                    )
        }         
    return {
        'statusCode': 200,
        'body': json.dumps(''.join([
            'Successfully sent recommendation emails.'
        ]))
    }