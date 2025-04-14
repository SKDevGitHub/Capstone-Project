# How to Find Telegram P&D Channels

1. Put keywords in keywords.pump. Channel names containing these keywords will be searched for.
2. Run tg_channel_scraper.py. This will create a file called tg_scraped_channels.
3. Set up a telegram API account
4. Put your api_id in a file called api_id.secret. THIS FILE IS IN .gitignore FOR A REASON! NEVER ADD THIS FILE TO GIT!
5. Put your api_hash in a file called api_hash.secret. THIS FILE IS IN .gitignore FOR A REASON! NEVER ADD THIS FILE TO GIT!
6. Add blacklisted telegram channels to blacklisted_tg_channels.dump. These will not be joined
7. Run join_tg_channels.py. This will cause your client to join all the channels in blacklisted_tg_channels.dump.
    - Note: A single client can only join up to 500 telegram channels. The script will exit if you have already reached this maximum.
    - Note: If you get a FloodWaitError, make sure you wait that amount of time before re-running the script.
    - Note: The script will auto-wait the correct amount of time as long as it's running. But if you stop the script, you still have to wait.

# TODO

- Scrape exchange websites for telegram links
- Make a script that leaves all telegram channels in the blacklist
- Make a script that searches all joined telegram channels for common P&D phrases/qualities, and:
    - Leaves channels that don't have those phrases/qualities
    - Leaves channels that have been inactive for more than a month
- Make a script that searches joined telegram channels for invite links, then dumps them to a file called tg_scraped_channels_linked
- Make Discord equivalents to the scraper, joiner, and keyword searcher scripts
- Leverage Multiple telegram accounts, so that we can join more than 500 servers at once

- Collect data from APIS for KuCoin, Poloniex, Digifinex, Pump.fun, or scrape it if API is not free

# Once we're confident we've found enough P&D channels

- Make a script that searches all channels for messages within the last month, and puts them in a well-organized dataset
- Do some clustering on this data to hopefully remove outlier channels
- Find a way to search this data for token names, then look them up in exchange APIs
- Use methods from research papers to perform predictions