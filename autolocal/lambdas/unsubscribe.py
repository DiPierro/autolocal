import json
from urllib.parse import urlencode

from autolocal.aws import aws_config
from autolocal.events import MailerEvent
from autolocal.emails import Email

class UnsubscribeEmail(Email):

    def _custom_init(self, **kwargs):
        
        # get information from query
        email_address = kwargs['email_address']
        
        # specify email contents
        self.recipient_address = list_if_str(email_address)
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


def lambda_handler_unsubscribe(aws_event, context):
    try:
        event = UnsubscribeEvent(aws_event)
        query_ids = event.get_query_ids()
    except Exception as e:
        raise e
        return {
                'statusCode': 400,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        }
    if not query_ids:
        return {
                'statusCode': 200,
                'body': ''.join([
                    'Email address {} '.format(event.email_address),
                    'was not found. You are not currently subscribed to emails.'
                ])
            }
    try:
        event.send_confirmation_email()
    except Exception as e:
        raise e
        return {
                'statusCode': 500,
                'body': json.dumps('Error while sending confirmation email: {}. You are not unsubscribed.'.format(e))
        }
    return {
                'statusCode': 200,
                'body': json.dumps(''.join([
                    'We sent a confirmation email to  {}. '.format(event.email_address),
                    'To finish unsubscribing, please check your inbox.'
                ]))
            }