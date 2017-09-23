'''
Linear regression algorithm for Poloniex.
'''

from datetime import datetime
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

__mongo_client__ = MongoClient()
__poloniex_mongo_collection__ = __mongo_client__.poloniex
__poloniex_tickers_regression__ = __poloniex_mongo_collection__.tickers_regression
__poloniex_trade_history_regression__ = __poloniex_mongo_collection__.trade_history_regression
__poloniex_zrx_trade_history__ = __poloniex_mongo_collection__.zrx_trade_history
__poloniex_chart_data__ = __poloniex_mongo_collection__.chart_data
style.use('ggplot')

def plot_results(real_data, test, forecast, date_times):
    '''
    Method that plots results of linear regression.
    '''
    t_test = numpy.arange(0, len(test), 1)
    t_forecast = numpy.arange(len(test)-1, len(test) + len(forecast) - 1, 1)

    plt.plot(date_times[:-len(forecast)], real_data, 'b', label='Real data')
    plt.plot(date_times[:-len(forecast)], test, 'r', label='Forecast test')
    plt.plot(date_times[len(test):], forecast, 'g', label='Forecast')
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.legend()
    plt.show()


def volume_prediction():
    '''
    Method for predicting buy, sell and wait actions.
    '''
    pickle_file = None
    df = None
    pickle_file = None
    try:
        pickle_file = open('volume_prediction.pickle', 'rb')
    except IOError:
        pickle_file = None
    if pickle_file is None:
        df = pandas.DataFrame(list(__poloniex_chart_data__.find({}, { 'date': 1, 'volume': 1, 'quoteVolume': 1, 'market': 1 }).sort([('date', pymongo.ASCENDING), ('market', pymongo.ASCENDING)])))
        df.set_index('date', inplace=True)
        df.drop(['_id'], 1, inplace=True)
        
        n_ticks_in_future = 6   # 1 tick is 5 minutess
        markets = list(set(df['market'].values))
        train_df = pandas.DataFrame()
        for market in markets:
            market_df = df.where(df['market'] == market).dropna()
            market_df['prediction_volume_percentage'] = (market_df['volume'].shift(-n_ticks_in_future) - market_df['volume']) / market_df['volume']
            market_df['prediction_volume_percentage'].replace([numpy.inf, -numpy.inf], numpy.NaN, inplace=True)
            buy_percentage = 0.4
            sell_percentage = -0.2
            market_df['prediction'] = [[[0, -1][chng_perc < sell_percentage], 1][chng_perc > buy_percentage] for chng_perc in market_df['prediction_volume_percentage']]
            market_df.dropna(inplace=True)
            train_df = train_df.append(market_df)

        with open('volume_prediction.pickle', 'wb') as f:
            pickle.dump(train_df, f)
    else:
        train_df = pickle.load(pickle_file)

    markets = list(set(train_df['market'].values))
    train_df.drop(['close', 'prediction_volume_percentage'], inplace=True)
    for market in markets:
        market_train_df = train_df.where(train_df['market'] == market).dropna()
        x, y = market_train_df.drop(['market', 'prediction'], 1).values, market_train_df['prediction'].values
        x_train, x_test, y_train, y_test = cross_validation.train_test_split(x, y, test_size=0.1)

        # classifier = VotingClassifier([('knc', neighbors.KNeighborsClassifier()),
        #                                 ('lsvc', svm.LinearSVC()),
        #                                 ('rfc', RandomForestClassifier()),
        #                                 ('dtc', DecisionTreeClassifier())])

        classifier = DecisionTreeClassifier()
        classifier.fit(x_train, y_train)
            
        accuracy = classifier.score(x_test, y_test)
        print('Market', market, ['\t', ''][len(market) > 7] + '\taccuracy:', accuracy)
        prediction = classifier.predict(x_test)
        print(Counter(prediction))
        print(Counter(y_test))


def price_regression():
    '''
    Method that predicts next price with linear regression.
    '''
    pickle_file = None
    try:
        pickle_file = open('price_regression.pickle', 'rb')
    except IOError:
        pickle_file = None
    
    classifier = None
    data = list(__poloniex_trade_history_regression__.find({ 'market': 'USDT_BTC' }).sort('date', pymongo.ASCENDING))
    filtered_data = numpy.array([[[0, 1][d['type'] == 'buy'], d['rate'], d['amount'], d['total'], float(time.mktime(time.strptime(d['date'], '%Y-%m-%d %H:%M:%S'))), d['rate'], datetime.strptime(d['date'], '%Y-%m-%d %H:%M:%S')] for d in data])
    for i in range(1, len(filtered_data)):
        filtered_data[i-1][-2] = filtered_data[i][-2]
    filtered_data = filtered_data[:-1]
    forecast_data = numpy.copy(filtered_data[-10:, :-2])
    if pickle_file is None:
        train_data = numpy.copy(filtered_data[:-10])
        # scaled_data = numpy.copy(train_data[:, :-2])
        # scaled_data = preprocessing.scale(scaled_data)

        x_train, x_test, y_train, y_test = cross_validation.train_test_split(train_data[:, :-2], train_data[:, -2], test_size=0.05)

        classifier = linear_model.LinearRegression(n_jobs=-1)
        classifier.fit(x_train, y_train)
            
        accuracy = classifier.score(x_test, y_test)
        print(accuracy)

        with open('price_regression.pickle', 'wb') as f:
            pickle.dump(classifier, f)
    else:
        classifier = pickle.load(pickle_file)
    
    start_test_index = -100
    # scaled_data = numpy.copy(filtered_data[start_test_index:-10, :-2])
    # scaled_data = preprocessing.scale(scaled_data)
    forecast_test = classifier.predict(filtered_data[start_test_index:-10, :-2])
	
    # scaled_data = numpy.copy(forecast_data)
    # scaled_data = preprocessing.scale(scaled_data)
    forecast_set = classifier.predict(forecast_data)

    plot_results(filtered_data[start_test_index:-10, -2], forecast_test, forecast_set, filtered_data[start_test_index:, -1])


def zrx_regression():
    pickle_file = None
    df = None
    try:
        pickle_file = open('zrx_regression.pickle', 'rb')
    except IOError:
        pickle_file = None
    if pickle_file is None:
        df = pandas.DataFrame(list(__poloniex_zrx_trade_history__.find({}, { 'date': 1, 'amount': 1, 'rate': 1, 'total': 1, 'type': 1, 'market': 1 })))
        df.drop(['_id'], 1, inplace=True)
        df.sort_index(inplace=True)

        with open('zrx_regression.pickle', 'wb') as f:
            pickle.dump(df, f)
    else:
        df = pickle.load(pickle_file)

    # df['prediction10'] = df['rate']
    # df.dropna(inplace=True)

    df.set_index('date', inplace=True)
    df['rate'].plot()
    plt.show()
    print(df.head())
    print(df.tail())


def main():
    volume_prediction()


if __name__ == "__main__":
    main()
