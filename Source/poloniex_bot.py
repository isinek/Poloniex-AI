'''
Poloniex bot
'''

from datetime import datetime, timedelta
import time
import logging
from pymongo import MongoClient
import poloniex_wrapper as pw

__poloniex_api_key__ = None
__poloniex_secret__ = None
__training__ = __poloniex_api_key__ is None or __poloniex_secret__ is None
__poloniex__ = pw.Poloniex(__poloniex_api_key__, __poloniex_secret__)
__log_formatter__ = logging.Formatter('-'*50 + '\n%(levelname)s: %(asctime)s\n%(message)s')
__log_file_handler__ = logging.FileHandler(datetime.today().strftime('%Y%m%d') + '_pb.log', mode='a')
__log_file_handler__.setFormatter(__log_formatter__)
__log__ = logging.getLogger('poloniex_bot_logger')
__log__.setLevel(logging.DEBUG)
__log__.addHandler(__log_file_handler__)
__mongo_client__ = MongoClient()
__poloniex_mongo_collection__ = __mongo_client__.poloniex
__poloniex_trade_history__ = __poloniex_mongo_collection__.trade_history
__poloniex_zrx_trade_history__ = __poloniex_mongo_collection__.zrx_trade_history
__poloniex_chart_data__ = __poloniex_mongo_collection__.chart_data

def get_trade_history_between_dates(start_date, end_date, currency_pairs=None, insert_to_database=False):
    '''
    Method that returns Poloniex trade history between two datetimes or inserts it into database.
    Examples:
        - Return all trades on 2017-01-01 for all markets (currency pairs):
            get_trade_history_between_dates(datetime(2017, 1, 1), datetime(2017, 1, 1, 23, 59, 59, 999999))
        - Return all trades on 2017-01-01 till noon for Bitcoin-Stellar and Bitcoin-FoldingCoin markets
            get_trade_history_between_dates(datetime(2017, 1, 1), datetime(2017, 1, 1, 12), ['BTC_STR', 'BTC_FLDC']
    '''
    if currency_pairs is None:
        currency_pairs = __poloniex__.get_all_markets()
    __log__.info('get_trade_history_between_dates(%s, %s, %s)',
                 start_date.strftime('%Y-%m-%d %H:%M:%S'),
                 end_date.strftime('%Y-%m-%d %H:%M:%S'),
                 '[' + ', '.join([pair for pair in currency_pairs]) + ']')
    trade_history = []
    for market in currency_pairs:
        current_date_start = start_date
        current_date_end = start_date + timedelta(days=1) - timedelta(microseconds=1)
        while current_date_start < end_date:
            if current_date_end > end_date:
                current_date_end = end_date
            __log__.info('__poloniex__.return_public_trade_history(%s, %s, %s)',
                         market,
                         current_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         current_date_end.strftime('%Y-%m-%d %H:%M:%S'))
            print('Market: %s, %s - %s' % (market, current_date_start.strftime('%Y-%m-%d %H:%M:%S'), current_date_end.strftime('%Y-%m-%d %H:%M:%S')))
            try:
                current_trade = __poloniex__.return_public_trade_history(market, current_date_start, current_date_end)
                for trade_part in current_trade:
                    trade_part['market'] = market
                if insert_to_database:
                    __poloniex_trade_history__.insert_many(current_trade)
                else:
                    trade_history += current_trade
                current_date_start += timedelta(days=1)
                current_date_end += timedelta(days=1)
            except Exception:
                __log__.exception('Public trade history method error')
    if not insert_to_database:
        return trade_history

def get_complete_trade_history(currency_start_date=datetime(2017, 1, 1), currency_pairs=None, mongo_collection=None):
    '''
    Method that returns Poloniex trade history between two datetimes or inserts it into database.
    Examples:
        - Return all trades on 2017-01-01 for all markets (currency pairs):
            get_trade_history_between_dates(datetime(2017, 01, 01), datetime(2017, 6, 22, 23, 59, 59, 999999))
        - Return all trades on 2017-01-01 till noon for Bitcoin-Stellar and Bitcoin-FoldingCoin markets
            get_trade_history_between_dates(datetime(2017, 01, 01), datetime(2017, 6, 22, 12), ['BTC_STR', 'BTC_FLDC'])
    '''
    if currency_pairs is None:
        currency_pairs = __poloniex__.get_all_markets()
        print('Jesi li siguran da zelis nastaviti sa dohvatom svih trzista?')
        c = input()
        if c.toLower() == 'n':
            return
    start_date = currency_start_date
    end_date = datetime.now()
    __log__.info('get_trade_history_between_dates(%s, %s, %s)',
                 start_date.strftime('%Y-%m-%d %H:%M:%S'),
                 end_date.strftime('%Y-%m-%d %H:%M:%S'),
                 '[' + ', '.join([pair for pair in currency_pairs]) + ']')
    trade_history = []
    for market in currency_pairs:
        current_date_start = start_date
        current_date_end = start_date + timedelta(days=1) - timedelta(microseconds=1)
        while current_date_start < end_date:
            if current_date_end > end_date:
                current_date_end = end_date
            __log__.info('__poloniex__.return_public_trade_history(%s, %s, %s)',
                         market,
                         current_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         current_date_end.strftime('%Y-%m-%d %H:%M:%S'))
            print('Market: %s, %s - %s' % (market, current_date_start.strftime('%Y-%m-%d %H:%M:%S'), current_date_end.strftime('%Y-%m-%d %H:%M:%S')))
            try:
                current_trade = __poloniex__.return_public_trade_history(market, current_date_start, current_date_end)
                for trade_part in current_trade:
                    trade_part['market'] = market
                if mongo_collection is not None:
                    mongo_collection.insert_many(current_trade)
                else:
                    trade_history += current_trade
                if current_date_end + timedelta(days=1) > end_date:
                    current_date_start = current_date_end
                    time.sleep(60)
                    current_date_end = end_date = datetime.now()
                else:
                    current_date_start += timedelta(days=1)
                    current_date_end += timedelta(days=1)
            except Exception:
                __log__.exception('Public trade history method error')
    if mongo_collection is None:
        return trade_history


def get_chart_data_between_dates(start_date, end_date, period, currency_pairs=None, insert_to_database=True):
    '''
    
    '''
    if currency_pairs is None:
        currency_pairs = __poloniex__.get_all_btc_markets()
    __log__.info('get_chart_data_between_dates(%s, %s, %d, %s)',
                 start_date.strftime('%Y-%m-%d %H:%M:%S'),
                 end_date.strftime('%Y-%m-%d %H:%M:%S'),
                 period,
                 '[' + ', '.join([pair for pair in currency_pairs]) + ']')
    chart_data = []
    for market in currency_pairs:
        current_date_start = start_date
        current_date_end = start_date + timedelta(days=1) - timedelta(microseconds=1)
        atempt = {}
        while current_date_start < end_date:
            if current_date_end > end_date:
                current_date_end = end_date
            __log__.info('__poloniex__.return_chart_data(%s, %s, %s, %d)',
                         market,
                         current_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         current_date_end.strftime('%Y-%m-%d %H:%M:%S'),
                         period)
            print('Market: %s, %s - %s' % (market, current_date_start.strftime('%Y-%m-%d %H:%M:%S'), current_date_end.strftime('%Y-%m-%d %H:%M:%S')))
            if current_date_start.strftime('%Y%m%d%H%M%S') not in atempt:
                atempt[current_date_start.strftime('%Y%m%d%H%M%S')] = 1
            else:
                atempt[current_date_start.strftime('%Y%m%d%H%M%S')] += 1
            try:
                current_trade = __poloniex__.return_chart_data(market, current_date_start, current_date_end, period)
                for trade_part in current_trade:
                    trade_part['market'] = market
                    trade_part['date'] = datetime.fromtimestamp(int(trade_part['date']))
                    trade_part['high'] = float(trade_part['high'])
                    trade_part['low'] = float(trade_part['low'])
                    trade_part['open'] = float(trade_part['open'])
                    trade_part['close'] = float(trade_part['close'])
                    trade_part['volume'] = float(trade_part['volume'])
                    trade_part['quoteVolume'] = float(trade_part['quoteVolume'])
                    trade_part['weightedAverage'] = float(trade_part['weightedAverage'])
                if insert_to_database:
                    __poloniex_chart_data__.insert_many(current_trade)
                else:
                    chart_data += current_trade
                current_date_start += timedelta(days=1)
                current_date_end += timedelta(days=1)
            except Exception:
                __log__.exception('Public trade history method error')
            if current_date_start.strftime('%Y%m%d%H%M%S') in atempt and atempt[current_date_start.strftime('%Y%m%d%H%M%S')] == 5:
                current_date_start += timedelta(days=1)
                current_date_end += timedelta(days=1)
            #time.sleep(1)
    if not insert_to_database:
        return chart_data


def main():
    '''
    It all starts here...
    '''
    # get_trade_history_between_dates(datetime(2017, 8, 17, 7, 0), datetime(2017, 8, 18, 5, 47), None, True)
    # data = __poloniex__.return_order_book('BTC_ETH', 10)
    # print(data)
    # buy_result = __poloniex__.buy('BTC_ZRX', 0.000075, 120)
    # print(buy_result)
    # get_complete_trade_history(__poloniex_zrx_trade_history__)
    # print(get_complete_trade_history(datetime(2017, 8, 19), ['BTC_ZRX'], __poloniex_zrx_trade_history__))
    get_chart_data_between_dates(datetime(2017, 1, 1), datetime.now(), 300, 
        [#'BTC_DOGE', 
        #'BTC_NXT', 
        #'BTC_ETH', 
        #'BTC_STEEM', 
        # 'BTC_ETC'
        'BTC_BCN' #,
        # 'BTC_ZRX'
        ])

if __name__ == "__main__":
    main()
