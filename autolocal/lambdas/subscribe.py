import json

from autolocal.mailer.events import MailerEvent, SUBSCRIBED, PENDING, SUBSCRIBE_FORM_KEYS

class SubscribeEvent(MailerEvent):
    """
    Functions related to a subscription event

    """
    def _custom_init(self):
        # scrub inputs and create unique query ID
        self.form_data = {k: self._scrub_data(k) for k in SUBSCRIBE_FORM_KEYS}
        self.qid = self._compute_qid(self.form_data)
        self.form_data['id'] = self.qid
        self.email_address = self.form_data['email_address']
        pass

    def write_record_to_db(self):
        timestamps = {
            'subscribed_timestamp': self.event_timestamp,
            'most_recent_digest_timestamp': 'none',
        }
        subscription_status = self._timestamp_subscription_status(PENDING)
        self.form_data.update(timestamps)
        self.form_data.update(subscription_status)
        self._put_query(self.form_data)
        pass        

    def send_confirmation_email(self):
        m = ConfirmSubscriptionEmail(query=self.form_data)
        m.send()
        pass


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