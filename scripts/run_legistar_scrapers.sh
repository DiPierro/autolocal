#!/bin/bash
source /home/ubuntu/autolocal/scripts/conda_init.sh
echo $PATH
conda activate autolocal
echo $PYTHONPATH
python /home/ubuntu/autolocal/autolocal/scrapers/run_legistar_scraper.py --year 2019 
python /home/ubuntu/autolocal/autolocal/scrapers/run_legistar_scraper.py --year 2020