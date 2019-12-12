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

    def _custom_init(self, query):
        qid = query[id]
        url = 'http://citycouncilor.com/subconfirmed.html?qid={}'.format(qid)
        keywords = ', '.join(query['keywords'])
        municipalities = ', '.join(query['municipalities'])

        self.recipient_address = query['email_address']
        self.subject = 'CityCouncilor: Please Confirm Subscription'
        self.body_html = """
        <html>
        <head></head>
        <body>
        <h1>Welcome to CityCouncilor!<h1>
        <p>We received a request to subscribe this email address to email alerts with the following query:</p>
        <p>Keywords: {}</p>
        <p>Municipalities: {}</p>
        <p>We will email you twice a week with tips on upcoming public meetings that match this query.
        To confirm your subscription, please click 
        <a href={}>here</a>.
        </p>
        <p>If you did not sign up for emails from CityCouncilor, simply ignore this message.</p>
        <p>Feel free to email us with any questions at 
        <a href='mailto:contact@citycouncilor.com'>contact@citycouncilor.com</a>.
        </p>
        </body>
        </html>
        """.format(keywords, municipalities, url)
        self.body_text = """
        Welcome to CityCouncilor!\r\n
        We received a request to subscribe this email address to email alerts with the following query:\r\n
        Keywords: {}\r\n
        Municipalities: {}\r\n
        We will email you twice a week with tips on upcoming public meetings that match this query.
        To confirm your subscription, please visit the following URL:\r\n
        {}\r\n
        If you did not sign up for emails from CityCouncilor, simply ignore this message.
        Feel free to email us with any questions at contact@citycouncilor.com.
        """.format(keywords, municipalities, url)
        self.sender_name = 'CityCouncilor Agenda Bot'
        self.sender_address = 'list-manager@citycouncilor.com'




