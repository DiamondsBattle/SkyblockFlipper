# Skyblock Flipper
An optimized real-time skyblock flipper, only relying on live data in order to always be profitable.
No market data is stored, as the flipper finds gaps in a item's price, enabling the user to buy an item and immediately sell it for a higher price, making up the gap.

### Settings
- `base_url` - The base url of the Hypixel Auction House API
- `categories` - The categories of items to flip
- `exceptions` - Names of specific items to ignore
- `min_flip` - The minimum profit to make from a flip
- `min_price` - The minimum price of an item to flip
- `min_supply` - The minimum supply of an item to flip
- `webhook_url` - The webhook url to send flip data to
- `webhook_mentions` - Discord IDs of users mentioned on webhook execution

### Stats*
- Average time to find a flip: **1.5s**
- Average profit per hour: **80m**
- Flip precision: **>90%**

\* depending on Internet connection speed and flip settings 
