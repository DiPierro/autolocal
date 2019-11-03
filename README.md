# autolocal
## Automated Local News
A collection of tools for scraping, collecting, organizing, viewing, and analyzing municipal meeting minutes and agendas.

## Directory structure
`notebooks` - Jupyter notebooks for data analysis/exploratory stuff

`autolocal` - code

`data` - some sample data for exploration

## Dependencies

This works with the following packages/versions:

`python` 3.7

`dash` 1.3.0

`flask` 1.1.1

`pdfminer` 20181108

`pandas` 0.24.2

`beautifulsoup` 4.8.0

## Usage

From the `autolocal` directory, run `python deploy_meeting_table.py`, then go to `localhost:8050` in your web browser. This should pull up the meeting table web application.

