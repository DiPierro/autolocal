#!/bin/bash
source /home/ubuntu/autolocal/scripts/conda_init.sh
echo $PATH
conda activate autolocal
echo $PYTHONPATH 
python /home/ubuntu/autolocal/autolocal/scraper/run_legistar_scraper.py --year 2020