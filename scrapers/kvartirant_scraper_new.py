import requests
from datetime import datetime
import re
from bs4 import BeautifulSoup
from bs4.element import Tag
from time import sleep
import json


class KvartirantScraper:
    """Get data on flats available for rent from https://r.onliner.by/ak/ according to the desired settings"""
    def __init__(self):
        self.seen_urls = set()

    @staticmethod
    def clean_html(raw_html: str) -> str:
        """Removing html tags and multiple newlines/spaces"""
        clean_regex = re.compile('<.*?>')
        clean_text = re.sub(clean_regex, '', raw_html)
        clean_text = re.sub(r'(?:\n|\s{2,})', ' ', clean_text)
        return clean_text.strip()

    def construct_message(self, url: str, title: Tag, description: Tag, owner: Tag, price: Tag) -> str:
        cleared_title = self.clean_html(str(title))
        cleared_description = self.clean_html(str(description))
        cleared_owner = self.clean_html(str(owner))
        cleared_prices = self.clean_html(str(price))
        price_currency = re.findall(r"(\d+\$.+?)\"", str(price))

        return '{}\n{}\n{}\n{}\n{}\n{}'.format(url, cleared_title, cleared_description, cleared_owner,
                                               cleared_prices, price_currency)

    def main(self):
        """Main function, constructing message if there is something worth sending"""
        config_params = json.load(open("./configs/config_and_cookies.json", 'r'))
        headers = config_params['kvartirant_headers']
        params = config_params['kvartirant_params']
        cookies = config_params['kvartirant_cookies']

        url_regexp = re.compile(r"a href=\"(.+?)\"")

        message = ''

        session = requests.Session()
        for page_num in range(1, 10):  # if results are on several pages

            response = session.get('https://www.kvartirant.by/ads/flats/rent/?page={}'.format(page_num),
                                   headers=headers, params=params, cookies=cookies)  # page numeration is weird here

            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.find_all('div', {'class': 'title-obj'})
            descriptions = soup.find_all('div', {'class': 'bottom'})
            owners = soup.find_all('p', {'class': 'landlords'})
            prices = soup.find_all('p', {'class': 'price'})

            if not descriptions:  # page where there are no results, no point to check further
                break

            for title, description, owner, price in zip(titles, descriptions, owners, prices):
                try:
                    url = url_regexp.findall(str(title))[0]
                except IndexError:
                    continue

                if url not in self.seen_urls:
                    self.seen_urls.add(url)
                    message += '-'*20 + '\n' + self.construct_message(url, title, description, owner, price) + '\n'*2
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
