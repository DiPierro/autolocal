from datetime import datetime
from autolocal import AUTOLOCAL_HOME
from  subprocess import run
import os
import sys

# get timestamp and job id
timestamp = datetime.utcnow.isoformat()
job_id = 'legistar_scraper_' + timestamp

# get directories
scraping_dir = os.path.join(AUTOLOCAL_HOME, 'data', 'scraping')
legistar_scraper_path = os.path.join(AUTOLOCAL_HOME, 'autolocal', 'scraping', 'legistar_scraper.py')
log_path = os.path.join(scraping_dir, 'log.out')

# build and run command with logging
args = sys.argv[1:]
print(args)
scraper_command = [legistar_scraper_path, '--job_id', timestamp]  + args + ['>', log_path]
run(scraper_command)

# move log to s3 bucket
s3_path = 's3://legistar-scraper-logs/legistar_scraper/{}/log.out'.format(job_id)
aws_cmd = ['aws', 's3', 'mv', log_path, s3_path]
run(aws_command)