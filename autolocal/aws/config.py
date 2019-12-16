#  private conifg file

supported_municipalities = [
    "Alameda",
    "Burlingame",
    "Cupertino",
    "Hayward",
    "Hercules",
    "Metropolitan Transportation Commission",
    "Mountain View",
    "Oakland",
    "San Francisco",
    "San Jose",
    "San Leandro",
    "San Mateo County",
    "Santa Clara",
    "South San Francisco",
    "Stockton",
    "Sunnyvale",
]

api_urls = {
    'subscribeQuery': 'https://2nr3b6lltj.execute-api.us-west-1.amazonaws.com/prod/subscribeQuery',
    'unsubscribeQuery': 'https://9k2fkcj7pb.execute-api.us-west-1.amazonaws.com/prod/unsubscribeQuery',
    'confirmSubscription': 'https://t8srcd3tv2.execute-api.us-west-1.amazonaws.com/prod/confirmSubscription', 
    'confirmUnsubscribe': 'https://s3xrgs9aad.execute-api.us-west-1.amazonaws.com/prod/confirmUnsubscribe',    
}

email_addresses = {
    'contact': 'contact@agendawatch.org',
    'list_manager': 'list-manager@agendawatch.org',
    'agenda_bot': 'agenda-bot@agendawatch.org',
    'sender_name': 'Agenda Watch',
}

config = {
    'region_name': 'us-west-1',    
    'db_document_table_name': 'autolocal-documents',
    'db_query_table_name': 'autolocal-user-queries',
    'db_recommendation_table_name': 'autolocal-recommendations',
    's3_document_bucket_name': 'autolocal-documents',        
    'ses_region_name': 'us-west-2',
    'ses_configuration_set': 'autolocal-mailbot',
    'supported_municipalities': supported_municipalities,    
    'api_urls': api_urls,    
    'email_addresses': email_addresses,
}