from calendar import c
import requests
from datetime import datetime, timedelta, tzinfo
from time import time, sleep
import json
import sys
from pytz import timezone, UTC
from bs4 import BeautifulSoup

# ---------------------------------
#   Program config
# ---------------------------------
bot_config_file_name = "onion-master-config.conf"

# ---------------------------------
#   MORELE.NET config
# ---------------------------------
morele_weekdays = [1, 2, 3, 4, 5]
morele_hours = [(14, 1)]
morele_link = "https://www.morele.net/"

# ---------------------------------
#   XKOM-PL config
# ---------------------------------
xkom_weekdays = [1, 2, 3, 4, 5, 6, 7]
xkom_hours = [(10, 1), (22, 1)]
xkom_link = "https://www.x-kom.pl/goracy_strzal/"

# ---------------------------------
#   Epic games store config
# ---------------------------------
epic_games_link_free_game = "https://www.epicgames.com/store/en-US/free-games"
epic_games_free_games_api_link = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=PL&allowCountries=PL"
epic_games_latest_free_games = []

# ---------------------------------
#   GG.Deals config
# ---------------------------------
ggdeals_weekdays = [1, 2, 3, 4, 5, 6, 7]
ggdeals_hours = [(17, 1)]
ggdeals_link_cluster = "https://gg.deals/news/?availability=1&title=free&type=1,6"
ggdeals_link_only_humble_bundle = "https://gg.deals/eu/news/humble-bundle-free-games/"
ggdeals_link_news_younger_than = timedelta(days=1)
ggdeals_news_excluded_words = [ ["epic", "games"] ]

def send_info_sale(site:str, name:str, old_price:float, new_price:float, link:str=None) -> None:
    msg = f"{site}\n{name}\nOld Price: {old_price}\nNew Price: {new_price}"
    if link:
        msg += f"\n{link}"
    print(msg + "\n")
    try:
        telegram_send_msg(msg)
    except Exception as E:
        print(E)

def send_info_free_game(shop:str, name:str, link:str=None, end_date:datetime=None) -> None:
    msg = f"FREE GAME - {shop}\nTitle - {name}"
    if end_date:
        msg += f"\nDeadline - {end_date}"
    if link:
        msg += f"\n{link}"
    print(msg + "\n")
    try:
        telegram_send_msg(msg)
    except Exception as E:
        print(E)

def telegram_send_msg(message):
    if not DEBUG:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&disable_web_page_preview=true"
        requests.get(url).json()

def get_html(site_url):
    header = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)\
    Chrome/50.0.2661.75 Safari/537.36", "X-Requested-With": "XMLHttpRequest"}
    web_page = requests.get(site_url, headers=header).text
    return BeautifulSoup(web_page, "html.parser")

def check_site_by_weekday_and_hour(weekday, hour, site_weekdays, site_hours):
    return hour in site_hours and weekday in site_weekdays

def check_site_by_next_date(next_date, now):
    return next_date and UTC.localize(next_date) < now

def morele():
    print("Searching morele...\n")
    try:
        soup = get_html(morele_link)
        name = soup.find("div", {"class": "promo-box-name"})
        link = name.find("a", {})['href']
        name = str(name.text).replace('\n', '')
        old_price = soup.find("div", {"class": "promo-box-old-price"}).text
        new_price = soup.find("div", {"class": "promo-box-new-price"}).text
        send_info_sale(
            site="MORELE NET",
            name=name,
            old_price=old_price,
            new_price=new_price,
            link=link)
    except Exception as E:
        print(E)

def xkom():
    print("Searching xkom...\n")
    try:
        soup = get_html(xkom_link)
        name = soup.find("title", {}).text
        name = name.replace("Gorący strzał - ", "")
        tag_list = soup.find_all("span", {})
        old_price_found = False
        old_price = "not found"
        new_price = "not found"
        for tag in tag_list:
            if "zł" in tag.text:
                if not old_price_found:
                    old_price = tag.text
                    old_price_found = True
                else:
                    new_price = tag.text
                    break
        send_info_sale(
            site="X-KOM PL",
            name=name.replace(" - x-kom.pl", ""),
            old_price=old_price,
            new_price=new_price,
            link="https://www.x-kom.pl/goracy_strzal/")
    except Exception as E:
        print(E)

def ggdeals():
    ggdeals_get_posts(ggdeals_link_only_humble_bundle, "Searching ggdeals for humble bundle...\n", "Humble Bundle")
    ggdeals_get_posts(ggdeals_link_cluster, "Searching ggdeals for freebies...\n", "GG.Deals")
    
def ggdeals_get_posts(url, msg, shop):
    print(msg)
    try:
        soup = get_html(url)
        offer_list = soup.find("div", {"class":"news-list"})
        offers = offer_list.find_all("article", {"class":"hoverable-box"})
        utc_time = datetime.utcnow()

        for offer in offers:
            time_added = str(offer.find("time"))
            date_index_start = time_added.find("datetime=\"") + len("datetime=\"")
            date_index_end = time_added.find("\"", date_index_start + 2 )
            post_date = time_added[date_index_start:date_index_end]
            post_date = post_date[:post_date.find('+')]
            if not (utc_time - datetime.strptime(post_date, "%Y-%m-%dT%H:%M:%S") < ggdeals_link_news_younger_than):
                continue
            game_name = offer.find("h3", {"class":"news-title"}).text
            game_name = game_name.replace("FREE ", "")
            post_link = str(offer.find("a", {"class": "full-link"}))
            post_link_index_start = post_link.find("href=\"") + len("href=\"")
            post_link_index_end = post_link.find("\"", post_link_index_start + 2 )
            link = "gg.deals" + post_link[post_link_index_start:post_link_index_end]
            if not is_news_unwanted(game_name, ggdeals_news_excluded_words):
                send_info_free_game(
                    shop=shop,
                    name=game_name,
                    link=link)
    except Exception as E:
        print(E)

def is_news_unwanted(news:str, unwanted_words_set):
    news_words = news.lower().split(' ')
    for unwanted_words in unwanted_words_set:
        is_unwanted = True
        for word in unwanted_words:
            is_unwanted = is_unwanted and word in news_words
        if is_unwanted:
            print(f"Found unwanted news:\n{news}\nContaining: {unwanted_words}\n")
            return True
    return False

def epic_games_store(send_message=True):
    print("Searching epic games store for freebies...\n")
    try:
        egs_data = requests.get(epic_games_free_games_api_link).text
        data = json.loads(egs_data)
        titles = data["data"]["Catalog"]["searchStore"]["elements"]
        for title in titles:
            if not (title["promotions"] and title["promotions"]["promotionalOffers"]):
                continue
            for promotionalOffersNested in title["promotions"]["promotionalOffers"]:
                for item in promotionalOffersNested["promotionalOffers"]:
                    if not (item["discountSetting"] and item["discountSetting"]["discountPercentage"] == 0):
                        continue
                    utc_time = datetime.utcnow()
                    today = datetime.now()
                    time_zone_hour_diff = today - utc_time
                    start_date = datetime.strptime(item["startDate"],
                                                            '20%y-%m-%dT%H:%M:%S.%fZ') + time_zone_hour_diff
                    end_date = datetime.strptime(item["endDate"],
                                                            '20%y-%m-%dT%H:%M:%S.%fZ') + time_zone_hour_diff
                    if start_date < today < end_date:
                        if send_message:
                            send_info_free_game(
                                shop="Epic Games Store", 
                                name=title["title"], 
                                link=epic_games_link_free_game,
                                end_date=end_date  - timedelta(minutes=1, seconds=1))
                        else:
                            print(f"Found currently free EGS game {title['title']} ending {end_date}\n")
                        sites[epic_games_store].update({"next_date": end_date})
    except Exception as E:
        print(E)

def clock():
    while True:
        sleep(60.0 - time() % 60)
        now = datetime.now(timezone(TIMEZONE))
        weekday = now.weekday() + 1
        hour = now.hour
        minute = now.minute
        for key, value in sites.items():
            if value["schedule"] == "fixed_schedule" and check_site_by_weekday_and_hour(weekday, (hour, minute), value["weekdays"], value["hours"]):
                key()
            elif value["schedule"] == "fluid_period_schedule" and check_site_by_next_date(value["next_date"], now):
                key()

def start():
    # flex schedule
    epic_games_store(not SKIP_FIRST)
    
    # strict schedule
    if not SKIP_FIRST:
        # xkom()
        morele()
        ggdeals()
    clock()

sites = {
    morele: {"schedule": "fixed_schedule", "weekdays": morele_weekdays, "hours": morele_hours},
    # xkom: {"schedule": "fixed_schedule", "weekdays": xkom_weekdays, "hours": xkom_hours},
    epic_games_store: {"schedule": "fluid_period_schedule", "next_date": None},
    ggdeals: {"schedule": "fixed_schedule","weekdays": ggdeals_weekdays, "hours": ggdeals_hours }
}


DEBUG = "-d" in sys.argv[1:]
SKIP_FIRST = "-s" in sys.argv[1:]
TIMEZONE = "CET"

bot_config_file = open(bot_config_file_name)
bot_config = bot_config_file.read().split("\n")
bot_config_file.close()
TOKEN = next(x for x in bot_config if "token" in x).replace("token = ","")
CHAT_ID = next(x for x in bot_config if "chat_id" in x).replace("chat_id = ","")

start()