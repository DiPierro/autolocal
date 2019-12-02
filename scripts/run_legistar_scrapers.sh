#!/bin/bash
source /home/ubuntu/.bashrc
echo $PATH
conda activate autolocal
echo $PYTHONPATH
python /home/ubuntu/autolocal/autolocal/scrapers/run_legistar_scraper.py --year 2019 
python /home/ubuntu/autolocal/autolocal/scrapers/run_legistar_scraper.py --year 2020