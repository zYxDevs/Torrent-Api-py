import asyncio
import re
import time

import aiohttp
from bs4 import BeautifulSoup

from helper.asyncioPoliciesFix import decorator_asyncio_fix
from helper.html_scraper import Scraper


class x1337:
    def __init__(self):
        self.BASE_URL = "https://1337xx.to"
        self.LIMIT = None

    @decorator_asyncio_fix
    async def _individual_scrap(self, session, url, obj):
        try:
            async with session.get(url) as res:
                html = await res.text(encoding="ISO-8859-1")
                soup = BeautifulSoup(html, "lxml")
                try:
                    magnet = soup.select_one(".clearfix ul li a")["href"]
                    uls = soup.find_all("ul", class_="list")[1]
                    lis = uls.find_all("li")[0]
                    imgs = (soup.find("div", class_="torrent-tabs")).find_all("img")
                    if imgs and len(imgs) > 0:
                        obj["screenshot"] = [
                            img["src"].replace(".th", "") for img in imgs
                        ]
                    obj["category"] = lis.find("span").text
                    try:
                        poster = soup.select_one("div.torrent-image img")["src"]
                        if str(poster).startswith("//"):
                            obj["poster"] = f"https:{poster}"
                        elif str(poster).startswith("/"):
                            obj["poster"] = self.BASE_URL + poster
                    except:
                        pass
                    obj["magnet"] = magnet

                    obj["hash"] = re.search(r"([{a-f\d,A-F\d}]{32,40})\b", magnet)[
                        0
                    ]

                except IndexError:
                    pass
        except:
            return None

    async def _get_torrent(self, result, session, urls):
        tasks = []
        for idx, url in enumerate(urls):
            for obj in result["data"]:
                if obj["url"] == url:
                    task = asyncio.create_task(
                        self._individual_scrap(session, url, result["data"][idx])
                    )
                    tasks.append(task)
        await asyncio.gather(*tasks)
        return result

    def _parser(self, htmls):
        try:
            for html in htmls:
                soup = BeautifulSoup(html, "lxml")
                list_of_urls = []
                my_dict = {"data": []}
                trs = soup.select("tbody tr")
                for tr in trs:
                    td = tr.find_all("td")
                    if name := td[0].find_all("a")[-1].text:
                        url = self.BASE_URL + td[0].find_all("a")[-1]["href"]
                        list_of_urls.append(url)
                        seeders = td[1].text
                        leechers = td[2].text
                        date = td[3].text
                        size = td[4].text.replace(seeders, "")
                        uploader = td[5].find("a").text

                        my_dict["data"].append(
                            {
                                "name": name,
                                "size": size,
                                "date": date,
                                "seeders": seeders,
                                "leechers": leechers,
                                "url": url,
                                "uploader": uploader,
                            }
                        )
                    if len(my_dict["data"]) == self.LIMIT:
                        break
                try:
                    pages = soup.select(".pagination li a")
                    my_dict["current_page"] = int(pages[0].text)
                    tpages = pages[-1].text
                    if tpages == ">>":
                        my_dict["total_pages"] = int(pages[-2].text)
                    else:
                        my_dict["total_pages"] = int(pages[-1].text)
                except:
                    pass
                return my_dict, list_of_urls
        except:
            return None, None

    async def search(self, query, page, limit):
        async with aiohttp.ClientSession() as session:
            self.LIMIT = limit
            start_time = time.time()
            url = self.BASE_URL + f"/search/{query}/{page}/"
            return await self.parser_result(start_time, url, session)

    async def parser_result(self, start_time, url, session):
        htmls = await Scraper().get_all_results(session, url)
        result, urls = self._parser(htmls)
        if result != None:
            results = await self._get_torrent(result, session, urls)
            results["time"] = time.time() - start_time
            results["total"] = len(results["data"])
            return results
        return result

    async def trending(self, category, page, limit):
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            self.LIMIT = limit
            url = (
                self.BASE_URL + f"/popular-{category.lower()}"
                if category
                else f"{self.BASE_URL}/home/"
            )

            return await self.parser_result(start_time, url, session)

    async def recent(self, category, page, limit):
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            self.LIMIT = limit
            url = (
                (self.BASE_URL + f"/cat/{str(category).capitalize()}/{page}/")
                if category
                else f"{self.BASE_URL}/trending"
            )

            return await self.parser_result(start_time, url, session)

    async def search_by_category(self, query, category, page, limit):
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            self.LIMIT = limit
            url = (
                self.BASE_URL
                + f"/category-search/{query}/{category.capitalize()}/{page}/"
            )

            return await self.parser_result(start_time, url, session)
