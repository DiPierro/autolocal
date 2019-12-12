# collection of lambda handlers for various events
import json
from .events import SubscribeEvent
from .events import ConfirmSubscriptionEvent
from .events import UnsubscribeEvent

def lambda_handler_subscribe(aws_event, context):
    try:
        event = SubscribeEvent(aws_event)
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
                    'We sent a confirmation email to  {}. '.format(event.email_address),
                    'To finish subscribing, please check your inbox.'
                ]))
            }


def lambda_handler_confirm_subscription(aws_event, context):
    try:
        event = ConfirmSubscriptionEvent(aws_event)
    except Exception as e:
        return {
                'statusCode': 200,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        }    
    event.subscribe_query()
    return {
        'statusCode': 200,
        'body': json.dumps(''.join([
            'Email address has been subscribed: {}).'.format(event.email_address)
        ]))
    }


def lambda_handler_unsubscribe(aws_event, context):
    try:
        event = UnsubscribeEvent(aws_event)
        query_ids = event.get_query_ids()
    except Exception as e:
        raise e
        return {
                'statusCode': 200,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        }
    if not query_ids:
        return {
                'statusCode': 200,
                'body': json.dumps(''.join([
                    'Email address {} '.format(event.email_address),
                    'was not found. You are not currently subscribed to emails.'
                ]))
            }
    try:        
        event.unsubscribe_queries(query_ids)
        event.send_confirmation_email()
        return {
            'statusCode': 200,
            'body': json.dumps(''.join([
                'Email address has been unsubscribed from all mail: {}).'.format(event.email_address)
            ]))
        }
    except Exception as e:
        return {
            'statusCode': 200,
            'body': json.dumps('Error while unsubscribing email address: {}.'.format(e))
    }
        
