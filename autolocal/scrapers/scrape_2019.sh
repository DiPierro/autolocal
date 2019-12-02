export PYTHONPATH=/home/ubuntu/autolocal:$PYTHONPATH
/home/ubuntu/miniconda3/envs/autolocal/bin/python ~/autolocal/autolocal/scrapers/run_legistar_scraper.py --year 2019 1> ~/out/cron.out 2> ~/out/cron.out
/home/ubuntu/miniconda3/envs/autolocal/bin/python ~/autolocal/autolocal/scrapers/run_legistar_scraper.py --year 2020 1> ~/out/cron.out 2> ~/out/cron.out
