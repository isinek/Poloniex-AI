'''
Poloniex scraping bot
Its purpose is to get ticker data every minute and insert them it database.
'''

from datetime import datetime
import logging
import time
from pymongo import MongoClient
import poloniex_wrapper as pw

__poloniex__ = pw.Poloniex(None, None)
__log_formatter__ = logging.Formatter('-'*50 + '\n%(levelname)s: %(asctime)s\n%(message)s')
__log_file_handler__ = logging.FileHandler(datetime.today().strftime('%Y%m%d') + '_psb.log', mode='a')
__log_file_handler__.setFormatter(__log_formatter__)
__log__ = logging.getLogger('poloniex_scraping_bot_logger')
__log__.setLevel(logging.DEBUG)
__log__.addHandler(__log_file_handler__)
__mongo_client__ = MongoClient()
__poloniex_mongo_collection__ = __mongo_client__.poloniex
__poloniex_tickers__ = __poloniex_mongo_collection__.tickers

def get_new_ticker_data(insert_to_database=True):
    '''
    Method that returns Poloniex ticker data.
    Examples:
        - Insert ticker data to database:
            get_new_ticker_data()
        - Return ticker data:
            get_new_ticker_data(False)
    '''
    __log__.info('get_new_ticker_data()')
    try:
        tickers_dict = __poloniex__.return_ticker()
        tickers = []
        for market in tickers_dict:
            ticker = tickers_dict[market]
            ticker['market'] = market
            ticker['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tickers += [ticker]
        if insert_to_database:
            __poloniex_tickers__.insert_many(tickers)
    except Exception:
        __log__.exception('Public ticker data method error')
    if not insert_to_database:
        return tickers

def main():
    '''
    Get ticker data.
    '''
    while True:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        get_new_ticker_data()
        time.sleep(60)

if __name__ == "__main__":
    main()
