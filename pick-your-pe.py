import re
import aiohttp
from bs4 import BeautifulSoup as bs

ua = ""
sessKeyPattern = re.compile(r'peselection.xjtlu.edu.cn","sesskey":"(\w+)","loadingicon"')


class PE:
    def __init__(self,
                 session: aiohttp.ClientSession,
                 username: str,
                 password: str
                 ):
        self.session = session
        self.isLogin = False
        self.username = username
        self.password = password
        self.sessKey = None

        self.course_list = []

    @staticmethod
    def log_debug(cls, r):
        print(r)

    async def service(self):
        async with self.session.post(
                url=f"https://peselection.xjtlu.edu.cn/lib/ajax/service.php?sesskey={self.sessKey}",
                json=[
                    {
                        "index": 0,
                        "methodname": "core_fetch_notifications",
                        "args": {
                            "contextid": 1
                        }
                    }
                ]
        ) as resp:
            self.log_debug(self, await resp.text())

    async def auth(self):
        # async with self.session.get(
        #         url="https://peselection.xjtlu.edu.cn/login/index.php",
        # ) as resp:
        #     if resp.status == 200:
        #         # text = bs(await resp.text(), 'html.parser')
        #         text = await resp.text()
        #     else:
        #         text = ''
        #         pass
        # sessKey = sessKeyPattern.findall(text)[0]
        # self.sessKey = sessKey
        # self.log_debug(self, sessKey)

        async with self.session.post(
                url="https://peselection.xjtlu.edu.cn/login/index.php",
                data={
                    "username": self.username,
                    "password": self.password,
                    "rememberusername": 1,
                    "anchor": ""
                },
                allow_redirects=False
        ) as resp:
            # Location should be like this: https://peselection.xjtlu.edu.cn/login/index.php?testsession=fffff
            location = resp.headers.get("Location")

        # await self.session.get(url=location)

    async def _get_ture_link(self, link) -> str:
        async with self.session.get(url=link, allow_redirects=False) as resp:
            location = resp.headers.get("Location")
        if location:
            return location
        else:
            return ""  # a falsy

    async def get_course_list(self):
        async with self.session.get("https://peselection.xjtlu.edu.cn/my/") as resp:
            # self.log_debug(self, await resp.text())
            text = await resp.text()
            text = bs(text, 'html.parser')
        course_list_raw = text.find_all('div', attrs={'class': 'course_title'})

        cid = 0
        for course in course_list_raw:
            cid += 1
            href = course.find_all('a')[0]
            link = href.get('href')
            title = href.get('title')
            self.course_list.append({
                "id": cid,
                "link": link,
                "title": title,
                "true_link": await self._get_ture_link(link)
            })
            print(link, title)

    async def get_options(self, course_link="https://peselection.xjtlu.edu.cn/mod/choice/view.php?id=60"):
        async with self.session.get(
                url=course_link,

        ) as resp:
            text = await resp.text()
        text = bs(text, 'html.parser')
        ul = text.find_all('ul', attrs={'class': 'choices'})[0]
        options = text.find_all('li', attrs={'class': 'option'})
        for option in options:
            input = option.find('input')
            value = input.get('value')
            label = option.text
            print(value, label)

    async def submit_choice(self, id, answer):
        async with self.session.post(
                url="https://peselection.xjtlu.edu.cn/mod/choice/view.php",
                headers={

                },
                data={
                    "answer": answer,
                    "sesskey": self.sessKey,
                    "action": "makechoice",
                    "id": str(id)
                }
        ) as resp:
            pass


async def main():
    async with aiohttp.ClientSession(headers={"User-Agent": ua}) as session:
        app = PE(session, "fff", "fff")
        await app.auth()
        await app.get_course_list()
        await app.get_options()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
