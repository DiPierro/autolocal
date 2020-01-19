import json

from autolocal.events import MailerEvent

class ConfirmUnsubscribeEvent(MailerEvent):
    """
    Functions related to a confirm subscription event
    """    
    def _custom_init(self):                     
        self.email_address = self._scrub_data('email_address')
        pass

    def unsubscribe_queries(self):
        self._update_subscription_status_by_email_address(self.email_address, UNSUBSCRIBED)
        pass

def lambda_handler_confirm_unsubscribe(aws_event, context):
    try:
        data = aws_event['queryStringParameters']
        event = ConfirmUnsubscribeEvent(data)
    except Exception as e:
        return {
                'statusCode': 400,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        } 

    try:
        event.unsubscribe_queries()
    except Exception as e:
        return {
                'statusCode': 500,
                'body': json.dumps(
                    'Error while attempting to unsubscribe email address {}: {}.'.format(event.email_address, e)
                    )
        }         
    return {
        'statusCode': 200,
        'body': json.dumps(''.join([
            'Email address has been unsubscribed from all email: {}.'.format(event.email_address)
        ]))
    }
