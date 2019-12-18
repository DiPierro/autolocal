SENDER_NAME = "Agenda Watch Bot"
SENDER_ADDRESS = 'list-manager@agendawatch.org'
SUBJECT = 'Welcome to Agenda Watch!'
body_text = lambda s: "Welcome to Agenda Watch! This is a test email. {}\r\n".format(s)
body_html = lambda s: """<html>
<head></head>
<body>
  <h1>Welcome to Agenda Watch!</h1>
  <p>This is a test email. {}</p>
</body>
</html>
""".format(s)


from autolocal.mailer.emails import Email

def send_test_email(destination, contents=''):    
    m = Email(
          recipient_address=destination,
          subject=SUBJECT,        
          body_html=body_html(contents),
          body_text=body_text(contents),
          sender_name=SENDER_NAME,
          sender_address=SENDER_ADDRESS)

    m.send()


if __name__=='__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('destination', default='success')
    parser.add_argument('contents', default='')
    args = parser.parse_args()

    if args.destination in ['success', 'bounce', 'ooto', 'complaint']:
        destination = '{}@simulator.amazonses.com'.format(args.destination)
    else:
        destination = args.destination

    send_test_email(destination, contents)
