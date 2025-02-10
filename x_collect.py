import twint
import pandas as pd
from datetime import datetime, timedelta

import twint.storage
import twint.storage.panda

today = datetime.now()
yesterday = today - timedelta(days = 1)

since = yesterday.strftime('%Y-%m-%d')
until = today.strftime('%Y-%m-%d')

c = twint.Config()
c.Search = ['#cryptocurrency', '$eagles']
c.Limit = 1000
c.Since = since
c.Until = until
c.Pandas = True
c.Hide_output = True

twint.run.Search(c)

tweets_df = twint.storage.panda.Tweets_df
tweets_df.to_csv('crypto_trend.csv', index = False)