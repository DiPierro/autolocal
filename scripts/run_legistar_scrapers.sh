#!/bin/bash
source /home/ubuntu/.bashrc
conda activate autolocal
python /home/ubuntu/autolocal/autolocal/scrapers/run_legistar_scraper.py --year 2019 
python /home/ubuntu/autolocal/autolocal/scrapers/run_legistar_scraper.py --year 2020