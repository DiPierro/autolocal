from threading import Thread

from autolocal import WebApp, DocumentManager, scrapers

# load document manager
documents = DocumentManager()

# just for testing - load some documents
if len(documents.metadata)==0:
    print('loading documents:')
    documents.add_docs_from_csv('../data/misc/meeting_table_prototype_v3.csv')

# run scraper in its own thread
scraper_list = scrapers.init_scrapers(documents)

# scraper = Scraper(documents)
for scraper in scraper_list:
    scraper_thread = Thread(
        target=scraper.run,
        daemon=True
        )
    scraper_thread.start()

# run webapp in its own thread
webapp = WebApp(documents)
webapp_thread = Thread(
    target=webapp.run,
    )
webapp_thread.start()
