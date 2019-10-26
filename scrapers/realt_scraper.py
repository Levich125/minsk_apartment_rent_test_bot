import requests
from datetime import datetime
import json
from bs4 import BeautifulSoup
from bs4.element import Tag
import re
from typing import Tuple
from time import sleep


class RealtScraper:
    """Get data on flats available for rent from https://realt.by/ according to the desired settings"""
    MAX_DAYS = 3

    def __init__(self):
        # seen apartments will be stored here so the system won't spam with the same message
        self.seen_apartments = set()

    @staticmethod
    def clean_html(raw_html: str) -> str:
        """Removing html tags and multiple newlines/spaces"""
        clean_regex = re.compile('<.*?>')
        clean_text = re.sub(clean_regex, '', raw_html)
        clean_text = re.sub(r'(?:\n|\s{2,})', ' ', clean_text)
        return clean_text.strip()

    def process_title(self, title: Tag) -> Tuple:
        """Extract id, url and address from the title"""
        address = self.clean_html(str(title))
        r_url = re.compile(r'(a href=")(.+?)(")')
        try:
            url = r_url.findall(str(title))[0][1]
            idn = url.split('/')[-2]
        except IndexError:
            url = ''
            idn = ''
        return idn, url, address

    def main(self):
        """Main function, constructing message if there is something worth sending"""
        print("realt main")
        config_params = json.load(open("./configs/config_and_cookies.json", 'r'))
        headers = config_params['realt_headers']
        params = config_params['realt_params']
        cookies = config_params['realt_cookies']

        joined_message = ''
        response = requests.get('https://realt.by/rent/flat-for-long/', headers=headers, params=params,
                                cookies=cookies)

        # all this comes info from one page, we do not enter each of the apartment info url
        soup = BeautifulSoup(response.text, 'html.parser')
        descriptions = soup.find_all('div', {'class': 'bd-item-right'})
        titles = soup.find_all('div', {'class': 'title'})
        prices = soup.find_all('span', {'class': 'price-byr'})

        for i in range(len(titles)):
            idn, url, address = self.process_title(titles[i])
            if idn not in self.seen_apartments:  # no point in processing the apartments we have already seen
                self.seen_apartments.add(idn)
                description = self.clean_html(str(descriptions[i]))  # cleaning description

                upped = re.findall(r'(Обновлено: )(.+?)( Код)', description)
                try:
                    date_upped = datetime.strptime(upped[0][1], '%d.%m.%Y').date()
                    delta = (datetime.today().date() - date_upped).days
                except (IndexError, TypeError):
                    date_upped = None
                    delta = None

                if date_upped and delta <= self.MAX_DAYS:  # apartments no more than 3 days old
                    price = self.clean_html(str(prices[i]))

                    tel_no = re.findall(r'\+\d{3}[\s-]\d{2}[\s-]\d{3}[\s-]\d{2}[\s-]\d{2}', description)
                    tel_no = ' '.join([x.replace(' ', '').replace('-', '') for x in tel_no])

                    message = '{}\n{}\n{}\n{}\n{}\n{}\n{}\n\n'.format(
                        '-'*20, idn, address, price, url, tel_no, upped[0][1])
                    # adding all the required info about apartment to the message that will be sent
                    joined_message += message
                    # print(datetime.now(), 'realt new apartment')
        yield joined_message


if __name__ == '__main__':
    scraper = RealtScraper()
    while 1:
        cnt = next(scraper.main())
        if cnt:
            print(cnt)
        else:
            print('-')
        sleep(10)
