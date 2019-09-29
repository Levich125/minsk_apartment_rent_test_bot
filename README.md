# minsk_apartment_rent_test_bot
Test telegram bot made to help me find the apartment for rent. Fetches data from 3 sites

Main file is bot_main.py. It creates and call the corresponding scrapers and sends data to telegram.
In order for it to work, telegram bot ID and the required params for each scraper need to be set. I took curl links from the developer's console and converted them to python requests' headers, cookies and params using https://curl.trillworks.com/
