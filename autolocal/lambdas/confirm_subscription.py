import json
from urllib.parse import urlencode

from autolocal.aws import aws_config
from autolocal.events import MailerEvent
from autolocal.emails import Email, UNSUBSCRIBED, SUBSCRIBED, PENDING, SUBSCRIBE_FORM_KEYS



class ConfirmUnsubscribeEmail(Email):

    def _custom_init(self, **kwargs):
        
        # get information from query
        email_address = kwargs['email_address']        
        api_url = aws_config.api_urls['confirmUnsubscribe']
        get_params = urlencode({'email_address': email_address})
        url = '{}?{}'.format(api_url, get_params)

        # specify email contents
        self.recipient_address = list_if_str(email_address)
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

def lambda_handler_confirm_subscription(aws_event, context):
    try:
        data = aws_event['queryStringParameters']
        event = ConfirmSubscriptionEvent(data)
    except Exception as e:
        return {
                'statusCode': 400,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        } 
    try:
        event.subscribe_query()
    except Exception as e:
        return {
                'statusCode': 500,
                'body': json.dumps(
                    'Error while attempting to subscribe email address {}: {}.'.format(event.email_address, e)
                    )
        }         
    return {
        'statusCode': 200,
        'body': json.dumps(''.join([
            'Email address has been subscribed: {}.'.format(event.email_address)
        ]))
    }