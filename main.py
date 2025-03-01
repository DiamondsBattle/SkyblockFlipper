import logging as log
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from json import load
from operator import itemgetter
from threading import Thread
from time import time, sleep, perf_counter

from discord_webhook import DiscordEmbed, DiscordWebhook
from pyperclip import copy as wincopy
from requests import get

from item import SoldItem


class HereWeGoAgain:
    """
    Main class
    """
    def __init__(self) -> None:
        """
        Initializes the flipper
        :return:
        """
        try:
            with open('user_settings.json', 'r') as f:
                log.debug('Loading user settings from user_settings.json')
                settings = load(f)
        except FileNotFoundError:
            with open('default_settings.json', 'r') as f:
                log.warning('No user_settings.json found, using default settings')
                settings = load(f)

        self.min_price = settings['min_price']
        self.min_flip = settings['min_flip']
        self.min_supply = settings['min_supply']
        self.categories = settings['categories']
        self.exceptions = settings['exceptions']
        self.base_url = settings['base_url']
        self.webhook_url = settings['webhook_url']
        self.webhook_mentions = settings['webhook_mentions']
        self.wh_configured = True
        if not self.webhook_url:
            log.critical('Webhook URL not set, ignoring discord pings')
            self.wh_configured = False

        self.ah = None
        self.flips: list = []
        self.items: dict[str: [SoldItem]] = {'': [SoldItem(0, '', '')]}
        self.page_count: int = 0
        self.total_value: int = 0
        self.total_profit: int = 0
        self.cleaned_names: dict = {}
        self.last_ah_update: int = 0
        self.start_time: float = perf_counter()

        while True:
            self.update()
            sleep(.1)

    def update(self) -> None:
        """
        Refreshes the market if a new update is available
        :return:
        """
        self.ah = get(f'{self.base_url}?page=0').json()

        if self.ah['lastUpdated'] == self.last_ah_update:
            market_delay = time() - (self.last_ah_update / 1000)
            sleep_time = 50 - market_delay
            if sleep_time > 0:
                sleep(sleep_time)
                log.debug(f'Sleeping for {round(sleep_time)}s')
            return
        else:
            self.last_ah_update = self.ah['lastUpdated']
            log.info(f'Market updated !')

        log.debug('Updating flipper')

        self.page_count = self.ah['totalPages']
        log.debug(f'Page count : {self.page_count}')

        self.items = {}

        self.updateAllPages()
        # self.listItems()

        self.findFlips()
        ttime = round(perf_counter() - self.start_time, 2)
        pph = round((self.total_profit / ttime * 3600) / 1e6, 1)

        log.info(f'Total flip value {self.cleanInt(self.total_value)}')
        log.info(f'Total flip profit {self.cleanInt(self.total_profit)}')
        log.info(f'Elapsed time : {ttime}s')
        log.info(f'~{pph}m/h')

    def updateAllPages(self) -> None:
        """
        Updates local AH data
        :return:
        """
        start = perf_counter()

        with ThreadPoolExecutor() as executor:
            pool = []
            for count in range(self.page_count + 1):
                pool.append(executor.submit(self.addItemsFromPage, page=count))

        log.debug(f'Fetched {self.page_count} pages in {round(perf_counter() - start, 2)}s')

    def addItemsFromPage(self, page: int) -> None:
        """
        Fetches all items from a page
        :param int page:
        :return:
        """
        start_time = perf_counter()
        content = get(f'{self.base_url}?page={page}').json()['auctions']
        for item in content:
            if item['bin'] and item['category'] in self.categories:
                cleaned_name = self.cleanName(item['item_name'])
                if cleaned_name in self.exceptions:
                    continue

                sold_item = SoldItem(item['starting_bid'], item['uuid'], item['item_name'])
                if cleaned_name in self.items.keys():
                    self.items[cleaned_name].append(sold_item)
                else:
                    self.items[cleaned_name] = [sold_item]
                self.items[cleaned_name] = sorted(self.items[cleaned_name], key=itemgetter(0))

        end = perf_counter()
        end_total_time = end - start_time
        log.debug(f'Got items from page {page} in {round(end_total_time, 2)}s')

    def cleanName(self, name: str) -> str:
        """
        Removes any artifacts from an item's name
        :param name: Name of the item to clean
        :return: Cleaned name
        """
        original_name: str = name
        if name in self.cleaned_names:
            return self.cleaned_names[name]

        # Possible artifacts : ⚚✦➊➋➌➍➎✪◆✿
        trash: list[str] = ['✪', '◆', '✿', 'Stiff', 'Lucky', 'Jerry\'s', 'Dirty', 'Fabled', 'Suspicious', 'Gilded', 'Warped',
                 'Withered', 'Bulky', 'Stellar', 'Heated', 'Ambered', 'Fruitful', 'Magnetic', 'Fleet', 'Mithraic',
                 'Auspicious', 'Refined', 'Headstrong', 'Precise', 'Spiritual', 'Moil', 'Blessed', 'Toil', 'Bountiful',
                 'Candied', 'Submerged', 'Reinforced', 'Cubic', 'Warped', 'Undead', 'Ridiculous', 'Necrotic', 'Spiked',
                 'Jaded', 'Loving', 'Perfect', 'Renowned', 'Giant', 'Empowered', 'Ancient', 'Sweet', 'Silky', 'Bloody',
                 'Shaded', 'Gentle', 'Odd', 'Fast', 'Fair', 'Epic', 'Sharp', 'Heroic', 'Spicy', 'Legendary', 'Deadly',
                 'Fine', 'Grand', 'Hasty', 'Neat', 'Rapid', 'Unreal', 'Awkward', 'Rich', 'Clean', 'Fierce', 'Heavy',
                 'Light', 'Mythic', 'Pure', 'Smart', 'Titanic', 'Wise', 'Bizarre', 'Itchy', 'Ominous', 'Pleasant',
                 'Pretty', 'Shiny', 'Simple', 'Strange', 'Vivid', 'Godly', 'Demonic', 'Forceful', 'Hurtful', 'Keen',
                 'Strong', 'Superior', 'Unpleasant', 'Zealous']
        for artifact in trash:
            name = name.replace(artifact + ' ', '')
            name = name.replace(artifact, '')

        name = name.rstrip().lstrip()
        self.cleaned_names[original_name] = name

        return name

    def findFlips(self) -> None:
        """
        Reads stored AH data and finds potential flips
        :return:
        """
        for name, items in self.items.items():
            price1, uuid1, name1 = items[0]

            # Sufficient market supply ; Price higher than minimum ; Not an old flip
            if len(items) < self.min_supply or uuid1 in self.flips or price1 < self.min_price:
                continue

            price2, uuid2, name2 = items[1]  # Only exists if supply is >=2
            margin = price2 - price1

            if margin > (price2 / 10) and margin > self.min_flip:
                log.info(f'Flip : {name} - {self.cleanInt(price2)} -> {self.cleanInt(price1)}')
                wincopy(f'/viewauction {uuid1}')
                Thread(target=self.sendAlert, args=(items,)).start()

                self.total_profit += margin
                self.total_value += price1
                self.flips.append(uuid1)

    def listItems(self) -> None:
        """
        Lists all items in the market
        :return:
        """
        for name, items in self.items.items():
            log.debug(f'{name} ({len(items)})')

    @staticmethod
    def cleanInt(q: int) -> str:
        """
        Formats an integer with commas to improve readability
        :param q: Integer to format
        :return: String containing the formatted integer
        """
        q = str(q)[::-1]
        _ = ''
        c = 0
        for i in q:
            if c % 3 == 0 and c != 0:
                _ += ','
            _ += i
            c += 1
        return _[::-1]

    def logStats(self, item, profit, _time) -> None:  # TODO : stats tracking
        """
        Placeholder for future advanced statistics
        :param item:
        :param profit:
        :param _time:
        :return:
        """
        pass

    def sendAlert(self, item: list[SoldItem]) -> None:
        """
        Sends a webhook alert to Discord
        :param item: List of sold items of a specific item
        :return:
        """  # TODO : unclear
        if not self.wh_configured:
            return

        item1, item2 = item[0], item[1]

        wbh_allowed_mentions = {
            'users': self.webhook_mentions,
            'parse': [
                'everyone'
            ]
        }

        webhook = DiscordWebhook(
            url=self.webhook_url,
            content=' '.join([f'<@{i}>' for i in self.webhook_mentions]),
            allowed_mentions=wbh_allowed_mentions,
            rate_limit_retry=True,
        )
        embed = DiscordEmbed(
            title='Flip found !',
            description=item1.name,
            color='ff0000'
        )
        embed.add_embed_field(
            name='Lowest BIN :',
            value=self.cleanInt(item1.price)
        )
        embed.add_embed_field(
            name='Second lowest BIN :',
            value=self.cleanInt(item2.price)
        )
        embed.add_embed_field(
            name='Delay :',
            value=f'{round(time() - self.last_ah_update / 1000, 1)}s',
            inline=False
        )

        auction = f'/viewauction {item1.uuid}'
        embed.add_embed_field(
            name='Auction :',
            value=auction,
            inline=False,
        )
        webhook.add_embed(embed)
        webhook.execute()


if __name__ == '__main__':
    log.getLogger('urllib3').setLevel(log.WARNING)
    log.getLogger('discord_webhook').setLevel(log.WARNING)
    log.basicConfig(
        level=log.DEBUG,
        handlers=[
            log.FileHandler('logs/latest.log', mode='w', encoding='utf-8'),
            log.FileHandler(datetime.now().strftime('logs/%H-%M-%d-%m-%Y.log'), mode='w', encoding='utf-8'),
            log.StreamHandler(sys.stdout)
        ]
    )
    # File logging settings
    log.getLogger().handlers[0].setFormatter(log.Formatter('[%(name)s]-%(asctime)s-%(levelname)s-%(message)s'))
    log.getLogger().handlers[1].setFormatter(log.Formatter('[%(name)s]-%(asctime)s-%(levelname)s-%(message)s'))
    # Console printing settings
    log.getLogger().handlers[2].setLevel(log.INFO)
    log.getLogger().handlers[2].setFormatter(log.Formatter('%(message)s'))

    try:
        app = HereWeGoAgain()
    except KeyboardInterrupt:
        log.critical('User interrupted execution')
