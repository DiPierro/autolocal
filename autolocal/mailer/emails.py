from .mailers import SESMailer
from urllib.parse import urlencode
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
        # Implement ME
        pass




