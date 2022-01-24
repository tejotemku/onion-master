import telegram_send
import requests
import datetime
import time
import json
from bs4 import BeautifulSoup

# ---------------------------------
#   MORELE.NET
# ---------------------------------
morele_weekdays = [1, 2, 3, 4, 5]
morele_hours = [(14, 1)]

# ---------------------------------
#   XKOM-PL config
# ---------------------------------
xkom_weekdays = [1, 2, 3, 4, 5, 6, 7]
xkom_hours = [(10, 1), (22, 1)]

# ---------------------------------
#   Epic games store
# ---------------------------------
epic_free_game_link = "https://www.epicgames.com/store/en-US/free-games"
epic_games_free_games_api_link = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=PL&allowCountries=PL"


def send_info_sale(site, name, old_price, new_price, link=None):
    msg = f"{site}\n{name}\nOld Price: {old_price}\nNew Price: {new_price}"
    if link:
        msg += f"\n{link}"
    try:
        telegram_send_msg(msg)
    except Exception as E:
        print(E)


def send_info_free_game(site, name, link=None, end_date=None):
    msg = f"FREE GAME on - {site}\nTitle - {name}"
    if end_date:
        msg += f"\nDeadline - {end_date}"
    if link:
        msg += f"\n{link}"

    try:
        telegram_send_msg(msg)
    except Exception as E:
        print(E)


def telegram_send_msg(message):
    telegram_send.send(messages=[message],
                       conf="onion-master-config.conf",
                       disable_web_page_preview=True)


def get_html(site_url):
    header = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)\
    Chrome/50.0.2661.75 Safari/537.36", "X-Requested-With": "XMLHttpRequest"}
    web_page = requests.get(site_url, headers=header).text
    return BeautifulSoup(web_page, "html.parser")


def check_site_by_weekday(weekday, hour, site_weekdays, site_hours):
    return hour in site_hours and weekday in site_weekdays


def check_site_by_next_date(next_date, now):
    return next_date and next_date < now


def morele():
    try:
        soup = get_html("https://www.morele.net/")
        name = soup.find("div", {"class": "promo-box-name"})
        link = name.find("a", {})['href']
        name = str(name.text).replace('\n', '')
        old_price = soup.find("div", {"class": "promo-box-old-price"}).text
        new_price = soup.find("div", {"class": "promo-box-new-price"}).text
        send_info_sale(site="MORELE NET",
                       name=name,
                       old_price=old_price,
                       new_price=new_price,
                       link=link)
    except Exception as E:
        print(E)


def xkom():
    try:
        soup = get_html("https://www.x-kom.pl/goracy_strzal/")
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
        send_info_sale(site="X-KOM PL",
                       name=name.replace(" - x-kom.pl", ""),
                       old_price=old_price,
                       new_price=new_price,
                       link="https://www.x-kom.pl/goracy_strzal/")
    except Exception as E:
        print(E)


def epic_games_store(send_msg=True):
    try:
        egs_data = requests.get(epic_games_free_games_api_link).text
        data = json.loads(egs_data)
        titles = data["data"]["Catalog"]["searchStore"]["elements"]
        for title in titles:
            if title["promotions"]:
                if ["promotionalOffers"]:
                    for promotionalOffersNested in title["promotions"]["promotionalOffers"]:
                        for item in promotionalOffersNested["promotionalOffers"]:
                            if item["discountSetting"]:
                                if item["discountSetting"]["discountPercentage"] == 0:
                                    start_date = datetime.datetime.strptime(item["startDate"],
                                                                            '20%y-%m-%dT%H:%M:%S.%fZ') + datetime.timedelta(hours=1, minutes=1)
                                    end_date = datetime.datetime.strptime(item["endDate"],
                                                                          '20%y-%m-%dT%H:%M:%S.%fZ') + datetime.timedelta(hours=1, minutes=1)
                                    today = datetime.datetime.now()
                                    if start_date < today < end_date:
                                        if send_msg:
                                            send_info_free_game("Epic Games Store", title["title"], epic_free_game_link,
                                                                end_date)
                                        sites[epic_games_store].update({"next_date": end_date})
                                        print("found epic games store game ", title["title"])
    except Exception as E:
        print(E)


def clock():
    while True:
        time.sleep(60.0 - time.time() % 60)
        now = datetime.datetime.now()
        weekday = now.weekday() + 1
        hour = now.hour
        minute = now.minute
        for key, value in sites.items():
            if value["schedule"] == "fixed_schedule":
                if check_site_by_weekday(weekday, (hour, minute), value["weekdays"], value["hours"]):
                    key()
            elif value["schedule"] == "fluid_period_schedule":
                if check_site_by_next_date(value["next_date"], now):
                    key()


def start():
    epic_games_store(send_msg=True)
    xkom()
    morele()
    clock()


sites = {
    morele: {"schedule": "fixed_schedule", "weekdays": morele_weekdays, "hours": morele_hours},
    xkom: {"schedule": "fixed_schedule", "weekdays": xkom_weekdays, "hours": xkom_hours},
    epic_games_store: {"schedule": "fluid_period_schedule", "next_date": None}
}

# telegram_send.configure(conf="onion-master-config.conf", group=True)
start()
