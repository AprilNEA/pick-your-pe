import re
import os
import json
import aiohttp
from bs4 import BeautifulSoup as bs
from urllib import parse

ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
sessKeyPattern = re.compile(r'peselection.xjtlu.edu.cn","sesskey":"(\w+)","loadingicon"')


class PE:
    def __init__(self,
                 session: aiohttp.ClientSession,
                 username: str = '',
                 password: str = '',
                 local=None
                 ):
        self.session = session
        self.isLogin = False
        self.username = username
        self.password = password
        self.sessKey = None
        self.local = local

    @staticmethod
    def log_debug(cls, r):
        print(r)

    @staticmethod
    def log_info(cls, r):
        print(r)

    async def auth(self):
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
            pass
            # We don't need to test session, ffffff
            # Location should be like this: https://peselection.xjtlu.edu.cn/login/index.php?testsession=fffff
            # location = resp.headers.get("Location")

        async with self.session.get(
                url="https://peselection.xjtlu.edu.cn/my/",
        ) as resp:
            text = await resp.text()
        sessKey = sessKeyPattern.findall(text)[0]
        self.sessKey = sessKey

    async def _get_ture_link(self, link) -> str:
        async with self.session.get(url=link, allow_redirects=False) as resp:
            location = resp.headers.get("Location")
        if location:
            return location
        else:
            return ""  # a falsy

    async def _get_course_list(self):
        async with self.session.get("https://peselection.xjtlu.edu.cn/my/") as resp:
            # self.log_debug(self, await resp.text())
            text = await resp.text()
            text = bs(text, 'html.parser')
        course_list_raw = text.find_all('div', attrs={'class': 'course_title'})

        cid = 0
        course_list = {}
        for course in course_list_raw:
            cid += 1
            href = course.find_all('a')[0]
            link = href.get('href')
            title = href.get('title')
            course_list[cid] = {
                "link": link,
                "title": title,
                "true_link": await self._get_ture_link(link)
            }
        return course_list

    async def _get_options(self, course_link="https://peselection.xjtlu.edu.cn/mod/choice/view.php?id=60"):
        result = {}
        async with self.session.get(
                url=course_link,

        ) as resp:
            text = await resp.text()
        text = bs(text, 'html.parser')
        try:
            ul = text.find_all('ul', attrs={'class': 'choices'})[0]
            options = ul.find_all('li', attrs={'class': 'option'})

            for option in options:
                input = option.find('input')
                value = input.get('value')
                label = option.text
                result[value] = {
                    "name": label
                }
        except IndexError:
            self.log_info(self, "当前课程尚未更新, 请在选择前夕再次尝试!")
            self.log_info(self, "程序将退出")
            exit(1)
        return result

    async def _submit_choice(self, id, answer):
        async with self.session.post(
                url="https://peselection.xjtlu.edu.cn/mod/choice/view.php",
                data={
                    "answer": answer,
                    "sesskey": self.sessKey,
                    "action": "makechoice",
                    "id": str(id)
                }
        ) as resp:
            print(await resp.text())

    async def choice(self):
        course_list = await self._get_course_list()
        if len(course_list) != 1:
            course = course_list[1]
            # for course in course_list:
            #     pass
        else:
            course = course_list[1]
        self.log_info(self, f"当前选择的课程为{course['title']}")

        option_list = await self._get_options(course["true_link"])
        id = parse.parse_qs(parse.urlparse(course["true_link"]).query)["id"]
        for key, option in option_list.items():
            self.log_info(self, f"{key}: {option['name']}")
        key = input("请输入您要选择的项目编号:")

        while True:
            await self._submit_choice(id, key)


async def main(u, p):
    async with aiohttp.ClientSession(headers={"User-Agent": ua}) as session:
        app = PE(session, u, p)
        await app.auth()
        await app.choice()


if __name__ == '__main__':
    import asyncio

    print("""
 _______   _          __        ____  ____                         _______  ________  
|_   __ \ (_)        [  |  _   |_  _||_  _|                       |_   __ \|_   __  | 
  | |__) |__   .---.  | | / ]    \ \  / / .--.   __   _   _ .--.    | |__) | | |_ \_| 
  |  ___/[  | / /'`\] | '' <      \ \/ // .'`\ \[  | | | [ `/'`\]   |  ___/  |  _| _  
 _| |_    | | | \__.  | |`\ \     _|  |_| \__. | | \_/ |, | |      _| |_    _| |__/ | 
|_____|  [___]'.___.'[__|  \_]   |______|'.__.'  '.__.'_/[___]    |_____|  |________| 
                                                                                      
Github: https://github.com/AprilNEA/pick-your-pe
Author: AprilNEA (https://sku.moe)
                                                                                      
""")

    local_path = os.path.join(os.path.dirname(__file__), "session.json")

    if os.path.exists(local_path):
        print(f"检测到本地文件{local_path}\n")
        with open(local_path, 'r') as f:
            local = json.load(f)
    else:
        isLocal = input("未检测到本地文件, 是否持久化(Y/n)").lower()
        if not isLocal == 'n':
            local = {
                "username": "",
                "password": ""
            }

    u = input("请输入您的账户: ")
    p = input("请输入您的密码: ")
    asyncio.run(main(u, p))
