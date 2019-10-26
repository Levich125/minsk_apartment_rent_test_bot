import requests
from datetime import datetime
from dateutil import parser
from dateutil.tz import tzoffset
import json
from bs4 import BeautifulSoup
from collections import OrderedDict
import re
from typing import Dict, List
from time import sleep


class OnlinerScraper:
    """Get data on flats available for rent from https://r.onliner.by/ak/ according to the desired settings"""
    def __init__(self):

        self.prices = {}  # go check were there price changes for apartments (all changes, not just price drop)
        self.now = datetime.now(tz=tzoffset(None, 10800))

        # names and ids of the fields. OrderedDict is used since the first version was made on python 3.5.2
        self.subclasses = OrderedDict(
            [('Номера телефонов', 'apartment-info__sub-line apartment-info__sub-line_extended-bottom_condensed-alter'),
                ('Когда звонить',
                 'apartment-info__sub-line apartment-info__sub-line_extended apartment-info__sub-line_complementary'),
                ('Имя контакта', 'apartment-info__sub-line apartment-info__sub-line_extended'),
                ('Условия сдачи', 'apartment-conditions'),
                ('Присутствует/отсутствует', 'apartment-options__item'),
                ('Описание', 'apartment-info__sub-line apartment-info__sub-line_extended-bottom')
             ])

        self.message_pool = ''

    @staticmethod
    def clean_html(raw_html: str) -> str:
        """Removing html tags and multiple newlines/spaces"""
        clean_regex = re.compile('<.*?>')
        clean_text = re.sub(clean_regex, '', raw_html)
        clean_text = re.sub(r'(?:\n|\s{2,})', ' ', clean_text)
        return clean_text.strip()

    def check_price_changes(self, apartments: List[Dict]) -> None:
        """Check whether some prices have changed"""
        curr_prices = {x['id']: float(x['price']['converted']['USD']['amount']) for x in apartments}  # {id: price}
        for i in curr_prices:
            prev_price = self.prices.get(i)
            if prev_price and curr_prices[i] != prev_price:
                apartment = [x for x in apartments if x['id'] == i][0]  # id is unique, so only one apartment
                message = self.construct_message(
                    apartment, comment="Price changed from {} to {}!".format(prev_price, curr_prices[i]))

                self.message_pool += message + '\n'*3
        self.prices = curr_prices
        return

    def check_recent_entries(self, apartments: List[Dict], new_period: int = 12) -> None:
        """
        Check whether any of the collected apartments are new - created or upped in the last new_period seconds.
        :param apartments: list of apartments in the form of json
        :param new_period: period (in seconds) when the apartment is still considered as 'new'
         and sending a message is required.
        :return: None
        """

        for apartment in apartments:
            upped = parser.parse(apartment['last_time_up'])
            upped_ago = self.now - upped

            created = parser.parse(apartment['created_at'])
            created_ago = self.now - created

            if (upped_ago.days == 0 and upped_ago.seconds < new_period) or \
                    (created_ago.days == 0 and created_ago.seconds < new_period):
                # the newly created or upped apartment, adding its info in the message pool
                message = self.construct_message(apartment, comment='New apartment!')
                self.message_pool += message + '\n' * 3
        return

    def construct_message(self, apartment: Dict, comment: str = None) -> str:
        """Converts info on apartment from json to string that can be sent as a message"""
        rooms = {'room': 'комната', '1_room': '1-комн кв', '2_room': '2-комн кв', '3_room': '3-комн кв',
                 '4_room': '4-комн кв'}
        # comment can specify why the message is sent - is the apartment new, or the price has dropped
        if comment is None:
            initial = '-' * 20 + '\n' + '{}'.format(self.now.isoformat())
        else:
            initial = '-' * 20 + '\n' + '{}\n{}\n'.format(self.now.isoformat(), comment)
        updated = 'Обновлено  ' + apartment['last_time_up']
        created = 'Создано ' + apartment['created_at']

        is_owner = apartment['contact']['owner']  # Owner or agency?
        if is_owner:
            owner = 'СОБСТВЕННИК!!!\n'
        else:
            owner = 'Агентство\n'

        url = 'URL ' + apartment['url']  # link to the apartments info on onliner

        address = apartment['location']['address']
        # sometimes there can be bugs in location/address, so check both
        if not address:
            address = apartment['location']['user_address']
        address = 'Адрес ' + address
        price = 'Цена ' + apartment['price']['converted']['USD']['amount'] + '$\n'
        rooms = rooms.get(apartment['rent_type'], apartment['rent_type'])

        resp = requests.get(apartment['url'])
        soup = BeautifulSoup(resp.text, 'html.parser')

        elements = []
        for element in self.subclasses:

            if element == 'Присутствует/отсутствует':  # furniture, internet, balcony, TV, etc
                ls = soup.find_all('div', {'class': self.subclasses[element]})

                temp = []
                for item in ls:
                    cnt = str(item)
                    if 'lack' not in cnt:
                        is_present = '++'
                    else:
                        is_present = '--'
                    temp.append(is_present + self.clean_html(cnt))
                elements.append((element, '\n'.join(temp)))

            elif element == 'Номера телефонов':  # where to call - in the form suitable for instant call from telegram
                ls = soup.find_all('div', {'class': self.subclasses[element]})
                temp = []
                for item in ls:
                    it = self.clean_html(str(item))
                    it = it.replace(' ', '').replace('-', '').replace('+', '\n+')
                    temp.append(it)
                elements.append((element, '\n'.join(temp)))
            else:
                ls = soup.find_all('div', {'class': self.subclasses[element]})
                temp = []
                for item in ls:
                    temp.append(self.clean_html(str(item)))
                elements.append((element, '\n'.join(temp)))

                if element == 'Имя контакта' and temp[0].strip().lower() == 'агент':
                    owner = 'Лживое агентство'  # if owner name is "Агент" or something like this. Pretty common.
        additionals = ''
        for i in elements:
            additionals += '\n{}\n{}\n'.format(i[0], i[1])
        return """{}
        {}
        {}
        {}
        {}
        {}
        {}
        {}
        {}""".format(initial, updated, created, owner, url, address, price, rooms, additionals)

    def main(self):
        """Main function, constructing message if there is something worth sending"""
        config_params = json.load(open("./configs/config_and_cookies.json", 'r'))  # this params load takes ~315 microseconds.
        headers = config_params['onliner_headers']
        params = config_params['onliner_params']
        cookies = config_params['onliner_cookies']

        response = requests.get('https://ak.api.onliner.by/search/apartments',
                                headers=headers, params=params, cookies=cookies)
        response_json = response.json()['apartments']

        now = datetime.now(tz=tzoffset(None, 10800))
        self.now = now
        self.message_pool = ''

        self.check_recent_entries(response_json)  # are there any new apartments?
        self.check_price_changes(response_json)  # are there any apartments with changed price?

        yield self.message_pool


if __name__ == '__main__':
    scraper = OnlinerScraper()
    while 1:
        cnt = next(scraper.main())
        if cnt:
            print(cnt)
        else:
            print('-')
        sleep(10)
