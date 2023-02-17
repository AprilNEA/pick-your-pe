import re
import aiohttp
from bs4 import BeautifulSoup as bs

ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
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
        async with self.session.get(
                url=course_link,

        ) as resp:
            text = await resp.text()
        text = bs(text, 'html.parser')
        ul = text.find_all('ul', attrs={'class': 'choices'})[0]
        options = ul.find_all('li', attrs={'class': 'option'})
        result = {}
        for option in options:
            input = option.find('input')
            value = input.get('value')
            label = option.text
            result[value] = {
                "name": label
            }
        return result

    async def _submit_choice(self, id, answer):
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
        for key, option in option_list.items():
            self.log_info(self, f"{key}: {option['name']}")
        key = input("请输入您要选择的项目编号:")


async def main(u, p):
    async with aiohttp.ClientSession(headers={"User-Agent": ua}) as session:
        app = PE(session, u, p)
        await app.auth()
        await app.choice()


if __name__ == '__main__':
    import asyncio
    u = input("请输入您的账户: ")
    p = input("请输入您的密码: ")
    asyncio.run(main(u, p))
