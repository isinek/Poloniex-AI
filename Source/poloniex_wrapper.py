'''
Poloniex_wrapper is module for easy use of Poloniex APIs.
Class Poloniex has implemented public and trading API methods.

Examples:
    - for using just public API methods you don't need API Key and Secret:
        import poloniex_wrapper as pw
        __poloniex__ = pw.Poloniex(None, None)
        __poloniex__.return_24h_volume()

    - when you want to use trading API methods, you'll need API Key and Secret:
        import poloniex_wrapper as pw
        __poloniex__ = pw.Poloniex('xxx-xxx-xxx-xxx', b'0123456789abcdef')
        __poloniex__.return_balances()
'''

import urllib
from urllib.request import urlopen, Request
import urllib.error
import json
import time
import hmac
import hashlib
from datetime import datetime
import logging

def create_time_stamp(datestr, date_format="%Y-%m-%d %H:%M:%S"):
    '''
    Method that converts date and time string to timestamp.
    '''
    return time.mktime(time.strptime(datestr, date_format))

class ApiQueryParams:
    '''
    Class with names of api query parameters as constants.
    '''
    __account__ = 'account'
    __address__ = 'address'
    __amount__ = 'amount'
    __auto_renew__ = 'autoRenew'
    __command__ = 'command'
    __currency__ = 'currency'
    __currency_pair__ = 'currencyPair'
    __depth__ = 'depth'
    __duration__ = 'duration'
    __end__ = 'end'
    __fill_or_kill__ = 'fillOrKill'
    __from_account__ = 'fromAccount'
    __immediate_or_cancel__ = 'immediateOrCancel'
    __lending_rate__ = 'lendingRate'
    __limit__ = 'limit'
    __order_number__ = 'orderNumber'
    __payment_id__ = 'paymentId'
    __period__ = 'period'
    __post_only__ = 'postOnly'
    __rate__ = 'rate'
    __start__ = 'start'
    __to_account__ = 'toAccount'

class ApiPublicMethods:
    '''
    Class with names of public api methods as constants.
    '''
    __return_ticker__ = 'returnTicker'
    __return_24h_volume__ = 'return24hVolume'
    __return_order_book__ = 'returnOrderBook'
    __return_trade_history__ = 'returnTradeHistory'
    __return_chart_data__ = 'returnChartData'
    __return_currencies__ = 'returnCurrencies'
    __return_loan_orders__ = 'returnLoanOrders'

class ApiTradingMethods:
    '''
    Class with names of api trading methods as constants.
    '''
    __return_balances__ = 'returnBalances'
    __return_complete_balances__ = 'returnCompleteBalances'
    __return_deposit_addresses__ = 'returnDepositAddresses'
    __generate_new_address__ = 'generateNewAddress'
    __return_deposits_withdrawals__ = 'returnDepositsWithdrawals'
    __return_open_orders__ = 'returnOpenOrders'
    __return_trade_history__ = 'returnTradeHistory'
    __return_order_trades__ = 'returnOrderTrades'
    __buy__ = 'buy'
    __sell__ = 'sell'
    __cancel_order__ = 'cancelOrder'
    __move_order__ = 'moveOrder'
    __withdraw__ = 'withdraw'
    __return_fee_info__ = 'returnFeeInfo'
    __return_available_account_balances__ = 'returnAvailableAccountBalances'
    __return_tradable_balances__ = 'returnTradableBalances'
    __transfer_balance__ = 'transferBalance'
    __return_margin_account_summary__ = 'returnMarginAccountSummary'
    __margin_buy__ = 'marginBuy'
    __margin_sell__ = 'marginSell'
    __get_margin_position__ = 'getMarginPosition'
    __close_margin_position__ = 'closeMarginPosition'
    __create_loan_offer__ = 'createLoanOffer'
    __cancel_loan_offer__ = 'cancelLoanOffer'
    __return_open_loan_offers__ = 'returnOpenLoanOffers'
    __return_active_loans__ = 'returnActiveLoans'
    __return_lending_history__ = 'returnLendingHistory'
    __toggle_auto_renew__ = 'toggleAutoRenew'

class Poloniex:
    '''
    Class for communication with Poloniex web API.
    '''
    __url_root__ = 'https://poloniex.com/'

    def __init__(self, api_key, secret):
        self.api_key = api_key
        self.secret = secret
        self.markets = None
        log_formatter = logging.Formatter('-'*50 + '\n%(levelname)s: %(asctime)s\n%(message)s')
        log_file_handler = logging.FileHandler(datetime.today().strftime('%Y%m%d') + '_pw.log', mode='a')
        log_file_handler.setFormatter(log_formatter)
        self.log = logging.getLogger('poloniex_wrapper_logger')
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(log_file_handler)

    def post_process(self, before):
        '''
        Method adds timestamp from datetime string.
        '''
        after = before
        if 'return' in after and isinstance(after['return'], list):
            for x in range(len(after['return'])):
                if isinstance(after['return'][x], dict) and 'datetime' in after['return'][x] and 'timestamp' not in after['return'][x]:
                    after['return'][x]['timestamp'] = float(create_time_stamp(after['return'][x]['datetime']))
        return after

    def build_api_query_url(self, params):
        '''
        Method generates API query URL with parameters for API methods including command.
        '''
        query_url = Poloniex.__url_root__ + 'public'
        if params != None and any(params):
            query_url += '?' + '&'.join([p + '=' + str(params[p]) for p in params])
        return query_url

    def api_query(self, api_method_type, params):
        '''
        Method for sending requests to API.
        '''
        for key, val in params.copy().items():
            if val is not None:
                if isinstance(val, float):
                    params[key] = '{:.8f}'.format(val)
                else:
                    params[key] = val
            else:
                del params[key]

        if ApiQueryParams.__start__ in params and isinstance(params[ApiQueryParams.__start__], datetime):
            params[ApiQueryParams.__start__] = params[ApiQueryParams.__start__].timestamp()
        if ApiQueryParams.__end__ in params and isinstance(params[ApiQueryParams.__end__], datetime):
            params[ApiQueryParams.__end__] = params[ApiQueryParams.__end__].timestamp()

        if api_method_type is ApiPublicMethods:
            url_from_params = self.build_api_query_url(params)
            self.log.info('ApiPublicMethods\nURL open: %s', url_from_params)
            try:
                ret = urlopen(Request(url_from_params, headers={'User-Agent': 'Mozilla/5.0'}))
                return json.loads(ret.read())
            except Exception:
                self.log.exception('Communication error')
                return json.loads(None)
        elif api_method_type is ApiTradingMethods:
            params['nonce'] = int(time.time()*1000)
            post_data = urllib.parse.urlencode(params).encode()

            sign = hmac.new(self.secret, post_data, hashlib.sha512).hexdigest()
            headers = {
                'Sign': sign,
                'Key': self.api_key,
                'User-Agent': 'Mozilla/5.0'
            }

            self.log.info('ApiTradingMethods\nURL open: %s\nPost data: %s\nHeaders: %s',
                          self.__url_root__ + 'tradingApi',
                          post_data,
                          '{' + ', '.join('{}:{}'.format(key, [val, 'None'][val is None]) for key, val in headers.items()) + '}')
            try:
                ret = urlopen(Request(self.__url_root__ + 'tradingApi', post_data, headers))
                json_ret = json.loads(ret.read())
                return self.post_process(json_ret)
            except Exception:
                self.log.exception('Communication error')
                return json.loads(None)

    def get_all_markets(self):
        '''
        Get all markets from return_24h_volume public API method.
        '''
        if self.markets is None:
            self.markets = []
            volumes = self.return_24h_volume()
            for market in volumes:
                if isinstance(volumes[market], dict):
                    self.markets.append(market)
        return self.markets

    def get_all_btc_markets(self):
        '''
        Get all markets from return_24h_volume public API method.
        '''
        if self.markets is None:
            self.markets = []
            volumes = self.return_ticker()
            for market in volumes:
                if isinstance(volumes[market], dict) and market[:3] == 'BTC':
                    self.markets.append(market)
        return self.markets

    # Implementation of public API methods

    def return_ticker(self):
        '''
        Public API method: returnTicker

        Returns the ticker for all markets. Sample output:
        {"BTC_LTC":{"last":"0.0251","lowestAsk":"0.02589999","highestBid":"0.0251","percentChange":"0.02390438","baseVolume":"6.16485315","quoteVolume":"245.82513926"},"BTC_NXT":{"last":"0.00005730","lowestAsk":"0.00005710","highestBid":"0.00004903","percentChange":"0.16701570","baseVolume":"0.45347489","quoteVolume":"9094"}, ... }

        Call: https://poloniex.com/public?command=returnTicker
        '''
        return self.api_query(ApiPublicMethods,
                              {ApiQueryParams.__command__: ApiPublicMethods.__return_ticker__})

    def return_24h_volume(self):
        '''
        Public API method: return24Volume

        Returns the 24-hour volume for all markets, plus totals for primary currencies. Sample output:
        {"BTC_LTC":{"BTC":"2.23248854","LTC":"87.10381314"},"BTC_NXT":{"BTC":"0.981616","NXT":"14145"}, ... "totalBTC":"81.89657704","totalLTC":"78.52083806"}

        Call: https://poloniex.com/public?command=return24hVolume
        '''
        return self.api_query(ApiPublicMethods,
                              {ApiQueryParams.__command__: ApiPublicMethods.__return_24h_volume__})

    def return_order_book(self, currency_pair='all', depth=10):
        '''
        Public API method: returnOrderBook

        Returns the order book for a given market, as well as a sequence number for use with the Push API and an indicator specifying whether the market is frozen. You may set currencyPair to "all" to get the order books of all markets. Sample output:
        {"asks":[[0.00007600,1164],[0.00007620,1300], ... ], "bids":[[0.00006901,200],[0.00006900,408], ... ], "isFrozen": 0, "seq": 18849}

        Or, for all markets:
        {"BTC_NXT":{"asks":[[0.00007600,1164],[0.00007620,1300], ... ], "bids":[[0.00006901,200],[0.00006900,408], ... ], "isFrozen": 0, "seq": 149},"BTC_XMR":...}

        Call: https://poloniex.com/public?command=returnOrderBook&currencyPair=BTC_NXT&depth=10
        '''
        return self.api_query(ApiPublicMethods,
                              {
                                  ApiQueryParams.__command__: ApiPublicMethods.__return_order_book__,
                                  ApiQueryParams.__currency_pair__: currency_pair,
                                  ApiQueryParams.__depth__: depth
                              })

    def return_public_trade_history(self, currency_pair, start, end):
        '''
        Public API method: returnTradeHistory

        Returns the past 200 trades for a given market, or up to 50,000 trades between a range specified in UNIX timestamps by the "start" and "end" GET parameters. Sample output:
        [{"date":"2014-02-10 04:23:23","type":"buy","rate":"0.00007600","amount":"140","total":"0.01064"},{"date":"2014-02-10 01:19:37","type":"buy","rate":"0.00007600","amount":"655","total":"0.04978"}, ... ]

        Call: https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_NXT&start=1410158341&end=1410499372
        '''
        return self.api_query(ApiPublicMethods,
                              {
                                  ApiQueryParams.__command__: ApiPublicMethods.__return_trade_history__,
                                  ApiQueryParams.__currency_pair__: currency_pair,
                                  ApiQueryParams.__start__: start,
                                  ApiQueryParams.__end__: end
                              })

    def return_chart_data(self, currency_pair, start, end, period):
        '''
        Public API method: returnChartData

        Returns candlestick chart data. Required GET parameters are "currencyPair", "period" (candlestick period in seconds; valid values are 300, 900, 1800, 7200, 14400, and 86400), "start", and "end". "Start" and "end" are given in UNIX timestamp format and used to specify the date range for the data returned. Sample output:
        [{"date":1405699200,"high":0.0045388,"low":0.00403001,"open":0.00404545,"close":0.00427592,"volume":44.11655644,"quoteVolume":10259.29079097,"weightedAverage":0.00430015}, ...]

        Call: https://poloniex.com/public?command=returnChartData&currencyPair=BTC_XMR&start=1405699200&end=9999999999&period=14400
        '''
        return self.api_query(ApiPublicMethods,
                              {
                                  ApiQueryParams.__command__: ApiPublicMethods.__return_chart_data__,
                                  ApiQueryParams.__currency_pair__: currency_pair,
                                  ApiQueryParams.__start__: start,
                                  ApiQueryParams.__end__: end,
                                  ApiQueryParams.__period__: period
                              })

    def return_currencies(self, currency):
        '''
        Public API method: returnCurrencies

        Returns information about currencies.
        Sample output:
        {"1CR":{"maxDailyWithdrawal":10000,"txFee":0.01,"minConf":3,"disabled":0},"ABY":{"maxDailyWithdrawal":10000000,"txFee":0.01,"minConf":8,"disabled":0}, ... }

        Call: https://poloniex.com/public?command=returnCurrencies
        '''
        return self.api_query(ApiPublicMethods,
                              {
                                  ApiQueryParams.__command__: ApiPublicMethods.__return_currencies__,
                                  ApiQueryParams.__currency__: currency
                              })

    def return_loan_orders(self, currency):
        '''
        Public API method: returnLoanOrders

        Returns the list of loan offers and demands for a given currency, specified by the "currency" GET parameter. Sample output:
        {"offers":[{"rate":"0.00200000","amount":"64.66305732","rangeMin":2,"rangeMax":8}, ... ],"demands":[{"rate":"0.00170000","amount":"26.54848841","rangeMin":2,"rangeMax":2}, ... ]}

        Call: https://poloniex.com/public?command=returnLoanOrders&currency=BTC
        '''
        return self.api_query(ApiPublicMethods,
                              {
                                  ApiQueryParams.__command__: ApiPublicMethods.__return_loan_orders__,
                                  ApiQueryParams.__currency__: currency
                              })

    # Implementation of trading API methods

    def return_balances(self):
        '''
        Trading API method: returnBalances

        Returns all of your available balances. Sample output:
        {"BTC":"0.59098578","LTC":"3.31117268", ... }
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_balances__
                              })

    def return_complete_balances(self, account='all'):
        '''
        Trading API method: returnCompleteBalances

        Returns all of your balances, including available balance, balance on orders, and the estimated BTC value of your balance. By default, this call is limited to your exchange account; set the "account" POST parameter to "all" to include your margin and lending accounts. Sample output:
        {"LTC":{"available":"5.015","onOrders":"1.0025","btcValue":"0.078"},"NXT:{...} ... }
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_complete_balances__,
                                  ApiQueryParams.__account__: account
                              })

    def return_deposit_addresses(self):
        '''
        Trading API method: returnDepositAddresses

        Returns all of your deposit addresses. Sample output:
        {"BTC":"19YqztHmspv2egyD6jQM3yn81x5t5krVdJ","LTC":"LPgf9kjv9H1Vuh4XSaKhzBe8JHdou1WgUB", ... "ITC":"Press Generate.." ... }
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_deposit_addresses__
                              })

    def generate_new_address(self, currency):
        '''
        Trading API method: generateNewAddress

        Generates a new deposit address for the currency specified by the "currency" POST parameter. Sample output:
        {"success":1,"response":"CKXbbs8FAVbtEa397gJHSutmrdrBrhUMxe"}

        Only one address per currency per day may be generated, and a new address may not be generated before the previously-generated one has been used.
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__generate_new_address__,
                                  ApiQueryParams.__currency__: currency
                              })

    def return_deposits_withdrawals(self, start, end):
        '''
        Trading API method: returnDepositsWithdrawals

        Returns your deposit and withdrawal history within a range, specified by the "start" and "end" POST parameters, both of which should be given as UNIX timestamps. Sample output:
        {"deposits":[{"currency":"BTC","address":"...","amount":"0.01006132","confirmations":10,"txid":"17f819a91369a9ff6c4a34216d434597cfc1b4a3d0489b46bd6f924137a47701","timestamp":1399305798,"status":"COMPLETE"},{"currency":"BTC","address":"...","amount":"0.00404104","confirmations":10, "txid":"7acb90965b252e55a894b535ef0b0b65f45821f2899e4a379d3e43799604695c","timestamp":1399245916,"status":"COMPLETE"}],"withdrawals":[{"withdrawalNumber":134933,"currency":"BTC","address":"1N2i5n8DwTGzUq2Vmn9TUL8J1vdr1XBDFg","amount":"5.00010000", "timestamp":1399267904,"status":"COMPLETE: 36e483efa6aff9fd53a235177579d98451c4eb237c210e66cd2b9a2d4a988f8e","ipAddress":"..."}]}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_deposits_withdrawals__,
                                  ApiQueryParams.__start__: start,
                                  ApiQueryParams.__end__: end
                              })

    def return_open_orders(self, currency_pair='all'):
        '''
        Trading API method: returnOpenOrders

        Returns your open orders for a given market, specified by the "currencyPair" POST parameter, e.g. "BTC_XCP". Set "currencyPair" to "all" to return open orders for all markets. Sample output for single market:
        [{"orderNumber":"120466","type":"sell","rate":"0.025","amount":"100","total":"2.5"},{"orderNumber":"120467","type":"sell","rate":"0.04","amount":"100","total":"4"}, ... ]
        Or, for all markets:
        {"BTC_1CR":[],"BTC_AC":[{"orderNumber":"120466","type":"sell","rate":"0.025","amount":"100","total":"2.5"},{"orderNumber":"120467","type":"sell","rate":"0.04","amount":"100","total":"4"}], ... }
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_open_orders__,
                                  ApiQueryParams.__currency_pair__: currency_pair
                              })

    def return_trade_history(self, currency_pair='all', start=None, end=None):
        '''
        Trading API method: returnTradeHistory

        Returns your trade history for a given market, specified by the "currencyPair" POST parameter. You may specify "all" as the currencyPair to receive your trade history for all markets. You may optionally specify a range via "start" and/or "end" POST parameters, given in UNIX timestamp format; if you do not specify a range, it will be limited to one day. Sample output:
        [{ "globalTradeID": 25129732, "tradeID": "6325758", "date": "2016-04-05 08:08:40", "rate": "0.02565498", "amount": "0.10000000", "total": "0.00256549", "fee": "0.00200000", "orderNumber": "34225313575", "type": "sell", "category": "exchange" }, { "globalTradeID": 25129628, "tradeID": "6325741", "date": "2016-04-05 08:07:55", "rate": "0.02565499", "amount": "0.10000000", "total": "0.00256549", "fee": "0.00200000", "orderNumber": "34225195693", "type": "buy", "category": "exchange" }, ... ]
        Or, for all markets:
        {"BTC_MAID": [ { "globalTradeID": 29251512, "tradeID": "1385888", "date": "2016-05-03 01:29:55", "rate": "0.00014243", "amount": "353.74692925", "total": "0.05038417", "fee": "0.00200000", "orderNumber": "12603322113", "type": "buy", "category": "settlement" }, { "globalTradeID": 29251511, "tradeID": "1385887", "date": "2016-05-03 01:29:55", "rate": "0.00014111", "amount": "311.24262497", "total": "0.04391944", "fee": "0.00200000", "orderNumber": "12603319116", "type": "sell", "category": "marginTrade" }, ... ],"BTC_LTC":[ ... ] ... }
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_trade_history__,
                                  ApiQueryParams.__currency_pair__: currency_pair,
                                  ApiQueryParams.__start__: start,
                                  ApiQueryParams.__end__: end
                              })

    def return_order_trades(self, order_number):
        '''
        Trading API method: returnOrderTrades

        Returns all trades involving a given order, specified by the "orderNumber" POST parameter. If no trades for the order have occurred or you specify an order that does not belong to you, you will receive an error. Sample output:
        [{"globalTradeID": 20825863, "tradeID": 147142, "currencyPair": "BTC_XVC", "type": "buy", "rate": "0.00018500", "amount": "455.34206390", "total": "0.08423828", "fee": "0.00200000", "date": "2016-03-14 01:04:36"}, ...]
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_order_trades__,
                                  ApiQueryParams.__order_number__: order_number
                              })

    def buy(self, currency_pair, rate, amount, fill_or_kill=None, immediate_or_cancel=None, post_only=None):
        '''
        Trading API method: buy

        Places a limit buy order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number. Sample output:
        {"orderNumber":31226040,"resultingTrades":[{"amount":"338.8732","date":"2014-10-18 23:03:21","rate":"0.00000173","total":"0.00058625","tradeID":"16164","type":"buy"}]}

        You may optionally set "fillOrKill", "immediateOrCancel", "postOnly" to 1. A fill-or-kill order will either fill in its entirety or be completely aborted. An immediate-or-cancel order can be partially or completely filled, but any portion of the order that cannot be filled immediately will be canceled rather than left on the order book. A post-only order will only be placed if no portion of it fills immediately; this guarantees you will never pay the taker fee on any part of the order that fills.
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__buy__,
                                  ApiQueryParams.__currency_pair__: currency_pair,
                                  ApiQueryParams.__rate__: rate,
                                  ApiQueryParams.__amount__: amount,
                                  ApiQueryParams.__fill_or_kill__: fill_or_kill,
                                  ApiQueryParams.__immediate_or_cancel__: immediate_or_cancel,
                                  ApiQueryParams.__post_only__: post_only
                              })

    def sell(self, currency_pair, rate, amount, fill_or_kill=None, immediate_or_cancel=None, post_only=None):
        '''
        Trading API method: sell

        Places a sell order in a given market. Parameters and output are the same as for the buy method.
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__sell__,
                                  ApiQueryParams.__currency_pair__: currency_pair,
                                  ApiQueryParams.__rate__: rate,
                                  ApiQueryParams.__amount__: amount,
                                  ApiQueryParams.__fill_or_kill__: fill_or_kill,
                                  ApiQueryParams.__immediate_or_cancel__: immediate_or_cancel,
                                  ApiQueryParams.__post_only__: post_only
                              })

    def cancel_order(self, order_number):
        '''
        Trading API method: cancelOrder

        Cancels an order you have placed in a given market. Required POST parameter is "orderNumber". If successful, the method will return:
        {"success":1}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__cancel_order__,
                                  ApiQueryParams.__order_number__: order_number
                              })

    def move_order(self, order_number, rate, amount=None, post_only=None, immediate_or_cancel=None):
        '''
        Trading API method: moveOrder

        Cancels an order and places a new one of the same type in a single atomic transaction, meaning either both operations will succeed or both will fail. Required POST parameters are "orderNumber" and "rate"; you may optionally specify "amount" if you wish to change the amount of the new order. "postOnly" or "immediateOrCancel" may be specified for exchange orders, but will have no effect on margin orders. Sample output:
        {"success":1,"orderNumber":"239574176","resultingTrades":{"BTC_BTS":[]}}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__move_order__,
                                  ApiQueryParams.__order_number__: order_number,
                                  ApiQueryParams.__rate__: rate,
                                  ApiQueryParams.__amount__: amount,
                                  ApiQueryParams.__post_only__: post_only,
                                  ApiQueryParams.__immediate_or_cancel__: immediate_or_cancel
                              })

    def withdraw(self, currency, amount, address, payment_id=None):
        '''
        Trading API method: withdraw

        Immediately places a withdrawal for a given currency, with no email confirmation. In order to use this method, the withdrawal privilege must be enabled for your API key. Required POST parameters are "currency", "amount", and "address". For XMR withdrawals, you may optionally specify "paymentId". Sample output:
        {"response":"Withdrew 2398 NXT."}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__withdraw__,
                                  ApiQueryParams.__currency__: currency,
                                  ApiQueryParams.__amount__: amount,
                                  ApiQueryParams.__address__: address,
                                  ApiQueryParams.__payment_id__: payment_id
                              })

    def return_fee_info(self):
        '''
        Trading API method: returnFeeInfo

        If you are enrolled in the maker-taker fee schedule, returns your current trading fees and trailing 30-day volume in BTC. This information is updated once every 24 hours.
        {"makerFee": "0.00140000", "takerFee": "0.00240000", "thirtyDayVolume": "612.00248891", "nextTier": "1200.00000000"}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_fee_info__
                              })

    def return_available_account_balances(self, account=None):
        '''
        Trading API method: returnAvailableAccountBalances

        Returns your balances sorted by account. You may optionally specify the "account" POST parameter if you wish to fetch only the balances of one account. Please note that balances in your margin account may not be accessible if you have any open margin positions or orders. Sample output:
        {"exchange":{"BTC":"1.19042859","BTM":"386.52379392","CHA":"0.50000000","DASH":"120.00000000","STR":"3205.32958001", "VNL":"9673.22570147"},"margin":{"BTC":"3.90015637","DASH":"250.00238240","XMR":"497.12028113"},"lending":{"DASH":"0.01174765","LTC":"11.99936230"}}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_available_account_balances__,
                                  ApiQueryParams.__account__: account
                              })

    def return_tradable_balances(self):
        '''
        Trading API method: returnTradableBalances

        Returns your current tradable balances for each currency in each market for which margin trading is enabled. Please note that these balances may vary continually with market conditions. Sample output:
        {"BTC_DASH":{"BTC":"8.50274777","DASH":"654.05752077"},"BTC_LTC":{"BTC":"8.50274777","LTC":"1214.67825290"},"BTC_XMR":{"BTC":"8.50274777","XMR":"3696.84685650"}}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_tradable_balances__
                              })

    def transfer_balance(self, currency, amount, from_account, to_account):
        '''
        Trading API method: transferBalance

        Transfers funds from one account to another (e.g. from your exchange account to your margin account). Required POST parameters are "currency", "amount", "fromAccount", and "toAccount". Sample output:
        {"success":1,"message":"Transferred 2 BTC from exchange to margin account."}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__transfer_balance__,
                                  ApiQueryParams.__currency__: currency,
                                  ApiQueryParams.__amount__: amount,
                                  ApiQueryParams.__from_account__: from_account,
                                  ApiQueryParams.__to_account__: to_account
                              })

    def return_margin_account_summary(self):
        '''
        Trading API method: returnMarginAccountSummary

        Returns a summary of your entire margin account. This is the same information you will find in the Margin Account section of the Margin Trading page, under the Markets list. Sample output:
        {"totalValue": "0.00346561","pl": "-0.00001220","lendingFees": "0.00000000","netValue": "0.00345341","totalBorrowedValue": "0.00123220","currentMargin": "2.80263755"}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_margin_account_summary__
                              })

    def margin_buy(self, currency_pair, rate, amount, lending_rate=None):
        '''
        Trading API method: marginBuy

        Places a margin buy order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". You may optionally specify a maximum lending rate using the "lendingRate" parameter. If successful, the method will return the order number and any trades immediately resulting from your order. Sample output:
        {"success":1,"message":"Margin order placed.","orderNumber":"154407998","resultingTrades":{"BTC_DASH":[{"amount":"1.00000000","date":"2015-05-10 22:47:05","rate":"0.01383692","total":"0.01383692","tradeID":"1213556","type":"buy"}]}}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__margin_buy__,
                                  ApiQueryParams.__currency_pair__: currency_pair,
                                  ApiQueryParams.__rate__: rate,
                                  ApiQueryParams.__amount__: amount,
                                  ApiQueryParams.__lending_rate__: lending_rate
                              })

    def margin_sell(self, currency_pair, rate, amount, lending_rate=None):
        '''
        Trading API method: marginSell

        Places a margin sell order in a given market. Parameters and output are the same as for the marginBuy method.
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__margin_sell__,
                                  ApiQueryParams.__currency_pair__: currency_pair,
                                  ApiQueryParams.__rate__: rate,
                                  ApiQueryParams.__amount__: amount,
                                  ApiQueryParams.__lending_rate__: lending_rate
                              })

    def get_margin_position(self, currency_pair='all'):
        '''
        Trading API method: getMarginPosition

        Returns information about your margin position in a given market, specified by the "currencyPair" POST parameter. You may set "currencyPair" to "all" if you wish to fetch all of your margin positions at once. If you have no margin position in the specified market, "type" will be set to "none". "liquidationPrice" is an estimate, and does not necessarily represent the price at which an actual forced liquidation will occur. If you have no liquidation price, the value will be -1. Sample output:
        {"amount":"40.94717831","total":"-0.09671314",""basePrice":"0.00236190","liquidationPrice":-1,"pl":"-0.00058655", "lendingFees":"-0.00000038","type":"long"}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__get_margin_position__,
                                  ApiQueryParams.__currency_pair__: currency_pair
                              })

    def close_margin_position(self, currency_pair):
        '''
        Trading API method: closeMarginPosition

        Closes your margin position in a given market (specified by the "currencyPair" POST parameter) using a market order. This call will also return success if you do not have an open position in the specified market. Sample output:
        {"success":1,"message":"Successfully closed margin position.","resultingTrades":{"BTC_XMR":[{"amount":"7.09215901","date":"2015-05-10 22:38:49","rate":"0.00235337","total":"0.01669047","tradeID":"1213346","type":"sell"},{"amount":"24.00289920","date":"2015-05-10 22:38:49","rate":"0.00235321","total":"0.05648386","tradeID":"1213347","type":"sell"}]}}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__close_margin_position__,
                                  ApiQueryParams.__currency_pair__: currency_pair
                              })

    def create_loan_offer(self, currency, amount, duration, auto_renew, lending_rate):
        '''
        Trading API method: createLoanOffer

        Creates a loan offer for a given currency. Required POST parameters are "currency", "amount", "duration", "autoRenew" (0 or 1), and "lendingRate". Sample output:
        {"success":1,"message":"Loan order placed.","orderID":10590}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__create_loan_offer__,
                                  ApiQueryParams.__currency__: currency,
                                  ApiQueryParams.__amount__: amount,
                                  ApiQueryParams.__duration__: duration,
                                  ApiQueryParams.__auto_renew__: auto_renew,
                                  ApiQueryParams.__lending_rate__: lending_rate
                              })

    def cancel_loan_offer(self, order_number):
        '''
        Trading API method: cancelLoanOffer

        Cancels a loan offer specified by the "orderNumber" POST parameter. Sample output:
        {"success":1,"message":"Loan offer canceled."}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__cancel_loan_offer__,
                                  ApiQueryParams.__order_number__: order_number
                              })

    def return_open_loan_offers(self):
        '''
        Trading API method: returnOpenLoanOffers

        Returns your open loan offers for each currency. Sample output:
        {"BTC":[{"id":10595,"rate":"0.00020000","amount":"3.00000000","duration":2,"autoRenew":1,"date":"2015-05-10 23:33:50"}],"LTC":[{"id":10598,"rate":"0.00002100","amount":"10.00000000","duration":2,"autoRenew":1,"date":"2015-05-10 23:34:35"}]}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_open_loan_offers__
                              })

    def return_active_loans(self):
        '''
        Trading API method: returnActiveLoans

        Returns your active loans for each currency. Sample output:
        {"provided":[{"id":75073,"currency":"LTC","rate":"0.00020000","amount":"0.72234880","range":2,"autoRenew":0,"date":"2015-05-10 23:45:05","fees":"0.00006000"},{"id":74961,"currency":"LTC","rate":"0.00002000","amount":"4.43860711","range":2,"autoRenew":0,"date":"2015-05-10 23:45:05","fees":"0.00006000"}],"used":[{"id":75238,"currency":"BTC","rate":"0.00020000","amount":"0.04843834","range":2,"date":"2015-05-10 23:51:12","fees":"-0.00000001"}]}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_active_loans__
                              })

    def return_lending_history(self, start, end, limit=None):
        '''
        Trading API method: returnLendingHistory

        Returns your lending history within a time range specified by the "start" and "end" POST parameters as UNIX timestamps. "limit" may also be specified to limit the number of rows returned. Sample output:
        [{ "id": 175589553, "currency": "BTC", "rate": "0.00057400", "amount": "0.04374404", "duration": "0.47610000", "interest": "0.00001196", "fee": "-0.00000179", "earned": "0.00001017", "open": "2016-09-28 06:47:26", "close": "2016-09-28 18:13:03" }]
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__return_lending_history__,
                                  ApiQueryParams.__start__: start,
                                  ApiQueryParams.__end__: end,
                                  ApiQueryParams.__limit__: limit
                              })

    def toggle_auto_renew(self, order_number):
        '''
        Trading API method: toggleAutoRenew

        Toggles the autoRenew setting on an active loan, specified by the "orderNumber" POST parameter. If successful, "message" will indicate the new autoRenew setting. Sample output:
        {"success":1,"message":0}
        '''
        return self.api_query(ApiTradingMethods,
                              {
                                  ApiQueryParams.__command__: ApiTradingMethods.__toggle_auto_renew__,
                                  ApiQueryParams.__order_number__: order_number
                              })
