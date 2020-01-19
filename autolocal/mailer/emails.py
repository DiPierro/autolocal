from autolocal.mailers import SESMailer

def list_if_str(x):
    if isinstance(x, str):
        return [x]
    else:
        return x


class Email(object):

    def __init__(
        self,
        recipient_addresses=None,
        subject=None,        
        body_html=None,
        body_text=None,
        sender_name=None,
        sender_address=None,   
        **kwargs     
        ):
        
        self.recipient_addresses = list_if_str(recipient_addresses)
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


