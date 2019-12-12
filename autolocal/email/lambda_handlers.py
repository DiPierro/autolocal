# collection of lambda handlers for various events
import json
from .events import SubscribeEvent
from .events import ConfirmSubscriptionEvent
from .events import UnsubscribeEvent

def lambda_handler_subscribe(event, context):
    try:
        event = SubscribeEvent(event)
    except Exception as e:
        return {
                'statusCode': 200,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        }
    try:
        event.write_record_to_db()
    except Exception as e:
        return {
                'statusCode': 200,
                'body': json.dumps('Error while writing to db: {}.'.format(e))
        }
    try:
        event.send_confirmation_email()
    except Exception as e:
        return {
                'statusCode': 200,
                'body': json.dumps('Error while sending confirmation email: {}.'.format(e))
        }
    return {
                'statusCode': 200,
                'body': json.dumps(''.join([
                    'We sent a confirmation email to  {}.'.format(email_address),
                    'Please check your inbox to confirm subscription.'
                ]))
            }


def lambda_handler_confirm_subscription(event, context):
    try:
        event = ConfirmSubscriptionEvent(event)
    except Exception as e:
        return {
                'statusCode': 200,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        }

def lambda_handler_unsubscribe(event, context):
    try:
        event = UnsubscribeEvent(event)
        query_ids = event.get_query_ids()
    except Exception as e:
        return {
                'statusCode': 200,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        }
    if not query_ids:
        return {
                'statusCode': 200,
                'body': json.dumps(''.join([
                    'Email address "{}" '.format(email_address),
                    'was not found. You are not currently subscribed.'
                ]))
            }
    else:
        try:
            event.unsubscribe_queries(query_ids)
        except Exception as e:
            return {
                'statusCode': 200,
                'body': json.dumps('Error while unsubscribing email address: {}.'.format(e))
        }



def lambda_handler(event, context):
    data = json.loads(event['body'])
    email_address = data['id']
    try:
        email_exists = remove_query(email_address)
        if email_exists:
            return {
                'statusCode': 200,
                'body': json.dumps(''.join([
                    'You have been unsubscribed (email address "{}").'.format(email_address)
                ]))
            }
        else:
            return {
                'statusCode': 200,
                'body': json.dumps(''.join([
                    'I did not find the email address "{}" '.format(email_address),
                    'in the database. You are not currently subscribed.'
                ]))
            }
    except Exception as e:
        return {
                'statusCode': 200,
                'body': json.dumps(''.join([
                    'Something did not work ',
                    'This is the email_address: {}. '.format(email_address),
                    'And here is the error message: {}.'.format(e)
                ]))
        }    