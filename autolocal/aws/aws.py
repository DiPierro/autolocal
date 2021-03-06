# AWS config
# this makes configuration constants available to other parts of the code base

try:
    from autolocal.aws.config import config
except:
    raise ImportError('Make sure to specify your AWS resource names in config.py')

class AWSConfig(object):

    def __init__(
        self, 
        db_document_table_name,
        db_query_table_name,
        db_recommendation_table_name,
        s3_document_bucket_name,
        region_name,
        ses_region_name,
        ses_configuration_set,
        supported_municipalities,
        api_urls,
        email_addresses
        ):
        
        self.db_document_table_name = str(db_document_table_name)
        self.db_query_table_name = str(db_query_table_name)
        self.db_recommendation_table_name = str(db_recommendation_table_name)
        self.s3_document_bucket_name = str(s3_document_bucket_name)
        self.region_name = str(region_name)
        self.ses_region_name = str(ses_region_name)
        self.ses_configuration_set = str(ses_configuration_set)
        self.supported_municipalities = list(supported_municipalities)
        self.api_urls = dict(api_urls)
        self.email_addresses = dict(email_addresses)

aws_config = AWSConfig(**config)