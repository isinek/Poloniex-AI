'''
Prediction algorithm for Poloniex.
'''

import sys
from datetime import datetime, timedelta
import logging
import time
from collections import Counter
import pymongo
from pymongo import MongoClient
import numpy
from sklearn import cross_validation, linear_model, svm, neighbors
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
import matplotlib.pyplot as plt
from matplotlib import style
import pickle
import pandas
import poloniex_wrapper as pw

__poloniex_api_key__ = None
__poloniex_secret__ = None
__poloniex__ = pw.Poloniex(__poloniex_api_key__, __poloniex_secret__)
__log_formatter__ = logging.Formatter('-'*50 + '\n%(levelname)s: %(asctime)s\n%(message)s')
__log_file_handler__ = logging.FileHandler(datetime.today().strftime('%Y%m%d') + '_pb.log', mode='a')
__log_file_handler__.setFormatter(__log_formatter__)
__log__ = logging.getLogger('poloniex_prediction_logger')
__log__.setLevel(logging.DEBUG)
__log__.addHandler(__log_file_handler__)
__mongo_client__ = MongoClient()
__poloniex_mongo_collection__ = __mongo_client__.poloniex
__poloniex_chart_data__ = __poloniex_mongo_collection__.chart_data
style.use('ggplot')

def volume_prediction(specific_market=None):
    '''
    Method for predicting buy, sell and wait actions.
    '''
    df = None
    pickle_file = None
    pickle_file_name = 'volume_prediction.pickle'
    pickle_classifier_file = None
    pickle_classifier_file_name = 'volume_prediction_classifier.pickle'
    if specific_market is not None:
        pickle_file_name = specific_market + '_' + pickle_file_name
        pickle_classifier_file_name = specific_market + '_' + pickle_classifier_file_name
    try:
        pickle_file = open(pickle_file_name, 'rb')
    except IOError:
        pickle_file = None
    n_ticks_in_future = 1   # 1 tick is 5 minutess
    if pickle_file is None:
        chart_data_linq = __poloniex_chart_data__.find({}, { 'date': 1, 'volume': 1, 'quoteVolume': 1, 'market': 1 }).sort([('date', pymongo.ASCENDING), ('market', pymongo.ASCENDING)])
        df = pandas.DataFrame(list(chart_data_linq))
        df.set_index('date', inplace=True)
        df.drop(['_id'], 1, inplace=True)
        
        markets = list(set(df['market'].values))
        train_df = pandas.DataFrame()
        for market in markets:
            if specific_market is not None and specific_market != market:
                continue
            market_df = df.where(df['market'] == market).dropna()
            market_df['prediction_volume_percentage'] = (market_df['volume'].shift(-n_ticks_in_future) - market_df['volume']) / market_df['volume']
            market_df['prediction_volume_percentage'].replace([numpy.inf, -numpy.inf], numpy.NaN, inplace=True)
            buy_percentage = 0.4
            sell_percentage = -0.2
            market_df['prediction'] = [[[0, -1][chng_perc < sell_percentage], 1][chng_perc > buy_percentage] for chng_perc in market_df['prediction_volume_percentage']]
            market_df.dropna(inplace=True)
            train_df = train_df.append(market_df)
        
        with open(pickle_file_name, 'wb') as f:
            pickle.dump(train_df, f)
    else:
        train_df = pickle.load(pickle_file)

    markets = list(set(train_df['market'].values))
    train_df.drop(['prediction_volume_percentage'], 1, inplace=True)
    for market in markets:
        market_train_df = train_df.where(train_df['market'] == market).dropna()
        x, y = market_train_df.drop(['market', 'prediction'], 1).values, market_train_df['prediction'].values
        x_train, x_test, y_train, y_test = cross_validation.train_test_split(x, y, test_size=0.1)

        try:
            pickle_classifier_file = open(pickle_classifier_file_name, 'rb')
        except IOError:
            pickle_classifier_file = None
        if pickle_classifier_file is None:
            classifier = VotingClassifier([('knc', neighbors.KNeighborsClassifier()),
                                        ('lsvc', svm.LinearSVC()),
                                        ('rfc', RandomForestClassifier()),
                                        ('dtc', DecisionTreeClassifier())])
            
            classifier.fit(x_train, y_train)

            accuracy = classifier.score(x_test, y_test)
            print('Market', market, ['\t', ''][len(market) > 7] + '\taccuracy:', accuracy)
            prediction = classifier.predict(x_test)
            print(Counter(prediction))
            print(Counter(y_test))
            print(sum([[[0, 0.5][prediction[i] == 0], 1][prediction[i] == y_test[i]] for i in range(len(prediction))]) / len(prediction))
        
            with open(pickle_classifier_file_name, 'wb') as f:
                pickle.dump(classifier, f)
        else:
            classifier = pickle.load(pickle_classifier_file)
            current_date_end = datetime.now()
            current_date_start = current_date_end - timedelta(minutes=5*n_ticks_in_future)
            period = 300*n_ticks_in_future
            __log__.info('__poloniex__.return_chart_data(%s, %s, %s, %d)',
                         market,
                         current_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         current_date_end.strftime('%Y-%m-%d %H:%M:%S'),
                         period)
            print('Market: %s, %s - %s' % (market, current_date_start.strftime('%Y-%m-%d %H:%M:%S'), current_date_end.strftime('%Y-%m-%d %H:%M:%S')))
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
                __poloniex_chart_data__.insert_many(current_trade)

                x_pred = pandas.DataFrame(list(current_trade))
                x_pred.set_index('date', inplace=True)
                x_pred.drop(['_id', 'high', 'low', 'open', 'close', 'weightedAverage', 'market'], 1, inplace=True)
                prediction = classifier.predict(x_pred)
                prediction_counter = Counter(prediction)
                print(prediction, prediction_counter)
                if prediction_counter[1] > prediction_counter[-1] and prediction_counter[1] > prediction_counter[0]:
                    print('buy')
                elif prediction_counter[-1] > prediction_counter[1] and prediction_counter[-1] > prediction_counter[0]:
                    print('sell')
                else:
                    print('wait')

            except Exception:
                __log__.exception('Public trade history method error')


def main():
    specific_market = None
    if len(sys.argv) > 1:
        specific_market = sys.argv[1]
        while True:
            volume_prediction(specific_market)
            time.sleep(1800)


if __name__ == "__main__":
    main()
