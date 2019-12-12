from .senders import SESSender

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
            engine = SESSender(**sender_args)
        else:
            raise ValueError('Sender not known: {}'.format(sender))
        
        # send email
        message = engine.send_email(self)
        return message


class ConfirmSubscriptionEmail(Email):

    def _custom_init(self, **kwargs):
        
        # get information from query
        query = kwargs['query']
        qid = query['id']
        url = 'http://citycouncilor.com/subconfirmed.html?qid={}'.format(qid)
        keywords = ', '.join(query['keywords'])
        municipalities = ', '.join(query['municipalities'])

        # specify email contents
        self.recipient_address = query['email_address']
        self.subject = 'CityCouncilor: Please Confirm Subscription'
        self.body_html = """
        <html>
        <head></head>
        <body>
        <h1>Please confirm your subscription to CityCouncilor</h1>
        <h3>We received a request to subscribe this email address to periodic, personalized email alerts.
        To confirm your subscription, please click 
        <a href={}>here</a>.
        </h3>
        <p>Keywords: {}</p>
        <p>Municipalities: {}</p>
        <p>If you did not sign up for emails from CityCouncilor, simply ignore this message.
        Feel free to email us with any questions at 
        <a href='mailto:contact@citycouncilor.com'>contact@citycouncilor.com</a>.
        </p>
        </body>
        </html>
        """.format(url, keywords, municipalities)
        self.body_text = """
        Please confirm your subscription to CityCouncilor\r\n
        We received a request to subscribe this email address to periodic, personalized email alerts.
        To confirm your subscription, please visit the following URL:\r\n        
        {}\r\n
        Keywords: {}\r\n
        Municipalities: {}\r\n        
        If you did not sign up for emails from CityCouncilor, simply ignore this message.
        Feel free to email us with any questions at contact@citycouncilor.com.
        """.format(url, keywords, municipalities)
        self.sender_name = 'CityCouncilor Agenda Bot'
        self.sender_address = 'list-manager@citycouncilor.com'


class UnsubscribeEmail(Email):

    def _custom_init(self, **kwargs):
        
        # get information from query
        email_address = kwargs['email_address']
        
        # specify email contents
        self.recipient_address = email_address
        self.subject = 'CityCouncilor: You are unsubscribed'
        self.body_html = """
        <html>
        <head></head>
        <body>
        <h1>You are now unsubscribed from CityCouncilor</h1>
        <h3>We won't email {} again.</h3>
        <p>If you did not mean to unsubscribe, or if you change your mind, sign up for a new alert at
        <a href=CityCouncilor.com>CityCouncilor.com</a>.
        Feel free to email us with any questions at 
        <a href='mailto:contact@citycouncilor.com'>contact@citycouncilor.com</a>.
        </p>
        </body>
        </html>
        """.format(email_address)
        self.body_text = """
        You are now unsubscribed from CityCouncilor\r\n
        We won't email {} again.\r\n
        If you did not mean to unsubscribe, or if you change your mind, sign up for a new alert at CityCouncilor.com.
        Feel free to email us with any questions at contact@citycouncilor.com.
        """.format(email_address)
        self.sender_name = 'CityCouncilor Agenda Bot'
        self.sender_address = 'list-manager@citycouncilor.com'




