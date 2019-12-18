# collection of lambda handlers for various events
import json
from .events import SubscribeEvent
from .events import ConfirmSubscriptionEvent
from .events import UnsubscribeEvent
from .events import ConfirmUnsubscribeEvent
from .events import RecommendationEvent

def lambda_handler_subscribe(aws_event, context):
    try:
        event = SubscribeEvent(aws_event)
    except Exception as e:
        return {
                'statusCode': 400,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        }
    try:
        event.write_record_to_db()
    except Exception as e:
        return {
                'statusCode': 500,
                'body': json.dumps('Error while accessing database: {}.'.format(e))
        }
    try:
        event.send_confirmation_email()
    except Exception as e:
        return {
                'statusCode': 500,
                'body': json.dumps('Error while sending confirmation email: {}. You are not subscribed.'.format(e))
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


def lambda_handler_unsubscribe(aws_event, context):
    try:
        event = UnsubscribeEvent(aws_event)
        query_ids = event.get_query_ids()
    except Exception as e:
        raise e
        return {
                'statusCode': 400,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        }
    if not query_ids:
        return {
                'statusCode': 200,
                'body': ''.join([
                    'Email address {} '.format(event.email_address),
                    'was not found. You are not currently subscribed to emails.'
                ])
            }
    try:
        event.send_confirmation_email()
    except Exception as e:
        raise e
        return {
                'statusCode': 500,
                'body': json.dumps('Error while sending confirmation email: {}. You are not unsubscribed.'.format(e))
        }
    return {
                'statusCode': 200,
                'body': json.dumps(''.join([
                    'We sent a confirmation email to  {}. '.format(event.email_address),
                    'To finish unsubscribing, please check your inbox.'
                ]))
            }
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

def lambda_handler_send_recommendation(aws_event, context):
    try:
        event = RecommendationEvent(aws_event)
    except Exception as e:
        return {
                'statusCode': 400,
                'body': json.dumps('Error while processing event data: {}.'.format(e))
        } 
    try:
        event.send_recommendation_emails()
    except Exception as e:
        return {
                'statusCode': 500,
                'body': json.dumps(
                    'Error while attempting to send recommendation emails: {}.'.format(e)
                    )
        }         
    return {
        'statusCode': 200,
        'body': json.dumps(''.join([
            'Successfully sent recommendation emails.'
        ]))
    }
        