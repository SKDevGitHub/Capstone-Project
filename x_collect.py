import json
from datetime import datetime, timedelta
from scrapfly import ScrapflyClient, ScrapeConfig
from scrapfly.browser import AsyncBrowserContext
import jmespath
import asyncio

# Scrapfly API key
SCRAPFLY_API_KEY = 'your_scrapfly_api_key'

# Initialize Scrapfly client
scrapfly = ScrapflyClient(key=SCRAPFLY_API_KEY)

async def fetch_tweets(query, since, until, max_tweets=1000):
    """
    Fetches tweets based on a query and date range.
    """
    tweets = []
    search_url = f'https://x.com/search?q={query}%20since%3A{since}%20until%3A{until}&src=typed_query'

    # Configure Scrapfly to use a browser context
    scrape_config = ScrapeConfig(
        url=search_url,
        browser=True,
        browser_context=AsyncBrowserContext(
            intercept_request=True,
            intercept_response=True
        )
    )

    # Perform the scrape
    result = await scrapfly.scrape(scrape_config)

    # Extract tweets from the intercepted responses
    for response in result.context['responses']:
        if 'TweetDetail' in response.url:
            data = json.loads(response.body)
            for entry in data['data']['threaded_conversation_with_injections']['instructions']:
                if entry['type'] == 'TimelineAddEntries':
                    for item in entry['entries']:
                        if item['entryId'].startswith('tweet-'):
                            tweet = jmespath.search('content.itemContent.tweet_results.result.legacy', item)
                            if tweet:
                                tweet_date = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S %z %Y')
                                if since <= tweet_date <= until:
                                    tweets.append(tweet)
                                    if len(tweets) >= max_tweets:
                                        return tweets
    return tweets

if __name__ == "__main__":
    query = "#YourCrypto OR $YourCrypto"  # Replace with your target cryptocurrency hashtags or symbols
    since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    until = datetime.now().strftime('%Y-%m-%d')
    tweets = asyncio.run(fetch_tweets(query, since, until))
    with open('tweets.json', 'w') as f:
        json.dump(tweets, f, indent=4)
