from threading import Thread

from autolocal import WebApp, Scraper, DocumentManager

# load document manager
documents = DocumentManager()

# just for testing - load some documents
if len(documents.metadata)==0:
    print('loading documents:')
    documents.add_docs_from_csv('../data/misc/meeting_table_prototype_v3.csv')

# run scraper in its own thread
scraper = Scraper(documents)
scraper_thread = Thread(
    target=scraper.scrape,
    daemon=True
    )
scraper_thread.start()

# run webapp in its own thread
webapp = WebApp(documents)
webapp_thread = Thread(
    target=webapp.run,
    )
webapp_thread.start()
