import requests
from datetime import datetime
import re
from bs4 import BeautifulSoup
from bs4.element import Tag
from time import sleep
from typing import Optional, Tuple
import json


class KvartirantScraper:
    """Get data on flats available for rent from https://r.onliner.by/ak/ according to the desired settings"""
    def __init__(self):

        self.seen_ids = set()

        self.first_run = True

    @staticmethod
    def find_url_address_id(description: Tag) -> Optional[Tuple]:
        """Search for url, address, id"""
        dt = re.findall(r'(<a href=\")(.+?)(\">)(.+?)(</a)', str(description))
        if dt:
            url = dt[0][1]
            address = dt[0][3]
            idn = url.split('/')[-2]
            return url, address, idn
        else:
            return None

    @staticmethod
    def clean_html(raw_html: str) -> str:
        """Removing html tags and multiple newlines/spaces"""
        clean_regex = re.compile('<.*?>')
        clean_text = re.sub(clean_regex, '', raw_html)
        clean_text = re.sub(r'(?:\n|\s{2,})', ' ', clean_text)
        return clean_text

    def construct_message(self, description: Tag, price: Tag) -> str:
        url, address, idn = self.find_url_address_id(description)
        cleared_description = self.clean_html(str(description))
        cleared_prices = self.clean_html(str(price))

        tel_num = re.findall(r'\+\d{3}[\s-]\d{2}[\s-]\d{3}[\s-]\d{2}[\s-]\d{2}', cleared_description)
        tel_num = tel_num[0].replace(' ', '').replace('-', '')

        icons_list = re.findall(r'icon_.+\.gif', str(description))
        icons_cleared = '\n'.join([re.sub(r'(?:icon_|.gif)', '', i) for i in icons_list])

        return '{}\n{}\n{}\n{}\n\nЕсть/Нет:\n{}\n\n{}'.format(url, address, cleared_prices,
                                                              tel_num, icons_cleared, cleared_description)

    def main(self):
        """Main function, constructing message if there is something worth sending"""
        config_params = json.load(open("./configs/config_and_cookies.json", 'r'))
        headers = config_params['kvartirant_headers']
        params = config_params['kvartirant_params']
        cookies = config_params['kvartirant_cookies']

        message = ''
        for page_num in range(1, 10):  # if results are on several pages

            response = requests.get('https://www.kvartirant.by/rent/flats/page/{}/'.format(page_num),
                                    headers=headers, params=params, cookies=cookies)

            soup = BeautifulSoup(response.text, 'html.parser')
            descriptions = soup.find_all('div', {'class': 'txt_box2'})
            prices = soup.find_all('div', {'class': 'price-box'})

            if not descriptions:  # page where there are no results, no point to check further
                self.first_run = False  # do not send message at the first call unlinke RealtScraper
                break

            for description, price in zip(descriptions, prices):
                rs = self.find_url_address_id(description)
                if rs:
                    url, addr, idn = rs
                    if idn not in self.seen_ids:
                        self.seen_ids.add(idn)
                        if not self.first_run:  # do not send message at the first call unlinke RealtScraper
                            message += '-'*20 + '\n' + self.construct_message(description, price) + '\n'*2
                            print(datetime.now(), "kvartirant new apartment")
        yield message


if __name__ == '__main__':
    a = KvartirantScraper()
    while 1:
        cnt = next(a.main())
        if cnt:
            print(cnt)
        else:
            print('-')
        sleep(60)
