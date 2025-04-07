#!/usr/bin/env python

import ccxt
from ccxt.base.errors import RequestTimeout
import pandas as pd
from datetime import datetime
from datetime import timedelta
import time
import sys

def to_timestamp(dt):
    return binance.parse8601(dt.isoformat())


def download(symbol, start, end):
    '''
    Download all the transaction for a given symbol from the start date to the end date
    @param symbol: the symbol of the coin for which download the transactions
    @param start: the start date from which download the transaction
    @param end: the end date from which download the transaction
    '''

    records = []
    since = start
    ten_minutes = 60000 * 10

    print('Downloading {} from {} to {}'.format(symbol, binance.iso8601(start), binance.iso8601(end)))

    # retrieve the most recent set of orders; returns a None if ticker not available
    #breakpoint()
    try:
        orders = binance.fetch_trades(symbol + '/BTC', limit=1000, params={'fetchTradesMethod':'publicGetHistoricalTrades'})
    except RequestTimeout:
        time.sleep(5)
        orders = binance.fetch_trades(symbol + '/BTC', limit=1000, params={'fetchTradesMethod':'publicGetHistoricalTrades'})
    except ccxt.BadSymbol:
        print("Coin not on Exchange")
        return None

    if len(orders) > 0:
        try:
            oldest_order_id = int(orders[0]['order'])
        except TypeError:
            try:
                oldest_order_id = int(orders[0]['id'])
            except TypeError:
                return None
        order_id_timestamp = orders[0]['timestamp']
    else:
        return None

    # walk backward through order id's until right time stamp
    while order_id_timestamp > since:
        #breakpoint()
        try:
            orders = binance.fetch_trades(symbol + '/BTC', limit=1000, params={'fetchTradesMethod':'publicGetHistoricalTrades', 'fromId':oldest_order_id-1000})
        except RequestTimeout:
            time.sleep(5)
            orders = binance.fetch_trades(symbol + '/BTC', limit=1000, params={'fetchTradesMethod':'publicGetHistoricalTrades', 'fromId':oldest_order_id-1000})
        except TypeError:
            return None

        try:
            prev_id = oldest_order_id
            try:
                oldest_order_id = int(orders[0]['order'])
            except TypeError:
                try:
                    oldest_order_id = int(orders[0]['id'])
                except TypeError:
                    return None
            if oldest_order_id == prev_id:
                print(datetime.fromtimestamp(orders[0]['timestamp']/1000))
                return None
        except TypeError:
            return None

        order_id_timestamp = orders[0]['timestamp']

    # record orders from since to end
    while since < end:
        #breakpoint()
        print('since: ' + binance.iso8601(since)) #uncomment this line of code for verbose download
        try:
            orders = binance.fetch_trades(symbol + '/BTC', limit=1000, params={'fetchTradesMethod':'publicGetHistoricalTrades', 'fromId':oldest_order_id})
        except RequestTimeout:
            time.sleep(5)
            orders = binance.fetch_trades(symbol + '/BTC', limit=1000, params={'fetchTradesMethod':'publicGetHistoricalTrades', 'fromId':oldest_order_id})

        if len(orders) > 0:
            try:
                oldest_order_id = int(orders[-1]['order']) + 1
            except TypeError:
                try:
                    oldest_order_id = int(orders[-1]['id']) + 1
                except TypeError:
                    return None
            latest_ts = orders[-1]['timestamp']
            if since != latest_ts:
                since = latest_ts
            else:
                since += ten_minutes

            for l in orders:
                records.append({
                    'symbol': l['symbol'],
                    'timestamp': l['timestamp'],
                    'datetime': l['datetime'],
                    'side': l['side'],
                    'price': l['price'],
                    'amount': l['amount'],
                    'btc_volume': float(l['price']) * float(l['amount']),
                })
        else:
            break

    return pd.DataFrame.from_records(records)


def download_binance(days_before=7, days_after=7):
    '''
    Download all the transactions for all the pumps in binance in a given interval
    @param days_before: the number of days before the pump
    @param days_after: the number of days after the pump
    '''

    df = pd.read_csv('pump_telegram.csv')
    binance_only = df[df['exchange'] == sys.argv[1]]

    for i, pump in binance_only.iterrows():
        symbol = pump['symbol']
        date = pump['date'] + ' ' + pump['hour']
        pump_time = datetime.strptime(date, "%Y-%m-%d %H:%M")
        before = to_timestamp(pump_time - timedelta(days=days_before))
        after = to_timestamp(pump_time + timedelta(days=days_after))
        # to comment out
        import os
        if os.path.exists('data/{}_{}'.format(symbol, str(date).replace(':', '.') + '.csv')):
            print(symbol)
            continue
        #
        df = download(symbol, before, after)
        try:
            df.to_csv('data/{}_{}'.format(symbol, str(date).replace(':', '.') + '.csv'), index=False)
        except:
            continue


if __name__ == '__main__':
    if sys.argv[1] == "binance":
        binance = ccxt.binance()
    elif sys.argv[1] == "coinbase":
        binance = ccxt.coinbaseexchange()
    elif sys.argv[1] == "kucoin":
        binance = ccxt.kucoin()
    binance.load_markets()

    if len(sys.argv) > 2:
        download_binance(days_before=int(sys.argv[2]), days_after=int(sys.argv[3]))
    else:
        download_binance()
