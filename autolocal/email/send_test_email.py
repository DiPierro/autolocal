SENDER_NAME = "CityCouncilor Agenda Bot"
SENDER_ADDRESS = 'agendabot@citycouncilor.com'
RECIPIENT = "chstock@stanford.edu"

SUBJECT = 'Welcome to CityCouncilor!'
BODY_TEXT = ("Welcome to CityCouncilor!\r\n"
             "This email was sent from send_test_email.py with Amazon SES using the "
             "AWS SDK for Python (Boto)."
            )

BODY_HTML = """<html>
<head></head>
<body>
  <h1>Welcome to CityCouncilor!</h1>
  <p>This email was sent from send_test_email.py with
    <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
    <a href='https://aws.amazon.com/sdk-for-python/'>
      AWS SDK for Python (Boto)</a>.</p>
</body>
</html>
            """    

from autolocal.email import Email

m = Email(
        recipient_address=RECIPIENT,
        subject=SUBJECT,        
        body_html=BODY_HTML,
        body_text=BODY_TEXT,
        sender_name=SENDER_NAME,
        sender_address=SENDER_ADDRESS)

m.send(sender_args={'logging_address': None})