import boto3
from botocore.exceptions import ClientError       
from autolocal.aws import aws_config 

class Mailer(object):
    """
    Base class for an interface to send emails
    """

    def __init__(self, **kwargs):
        pass

    def send_email(self, email):
        pass


class SESMailer(Mailer):
    """
    Class to send emails via Amazon SES.
    """    

    def __init__(
        self,
        aws_region=aws_config.ses_region_name,
        configuration_set=aws_config.ses_configuration_set,
        charset='UTF-8',        
        ):
        
        self.client = boto3.client(
            'ses',
            region_name=aws_region
            )
        self.charset = charset
        self.configuration_set = configuration_set
        

    def send_email(
        self,
        email
        ):
        try:
            # specify recipients
            destination = {'ToAddresses': [email.recipient_address]}

            # specify message
            message = {
                    'Body': {
                        'Html': {
                            'Charset': self.charset,
                            'Data': email.body_html
                        },
                        'Text': {
                            'Charset': self.charset,
                            'Data': email.body_text
                        },
                    },
                    'Subject': {
                        'Charset': self.charset,
                        'Data': email.subject
                    },
                }

            # specify sender
            source = '{} <{}>'.format(email.sender_name, email.sender_address)

            # assemble message
            contents = {
                'Destination': destination,
                'Message': message,
                'Source': source
            }

            # add configuration set
            if self.configuration_set:
                contents['ConfigurationSetName'] = self.configuration_set

            # send email
            response = self.client.send_email(**contents)

        # Display an error if something goes wrong. 
        except ClientError as e:
            print(e.response['Error']['Message'])
            return e.response
        else:
            return response


