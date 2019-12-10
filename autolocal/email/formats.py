from autolocal.email import SESSender

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

        self._init(**kwargs)

    def _init(self, **kwargs):  
        # Implement me      
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


class WelcomeEmail(Email):
    pass
