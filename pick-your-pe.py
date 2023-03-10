import re
import os
import json
import time

import aiohttp
from bs4 import BeautifulSoup as bs
from urllib import parse
from getpass import getpass
from datetime import datetime
from aiohttp.client_exceptions import ClientError, ClientConnectorCertificateError

ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
sessKeyPattern = re.compile(r'peselection.xjtlu.edu.cn","sesskey":"(\w+)","loadingicon"')

timeline = {
    "D1/01": {
        "start": 1676934000,
        "end": 1677081540
    },
    "D1/02": {
        "start": 1676934000,
        "end": 1677081540
    },
    "D1/03": {
        "start": 1676955600,
        "end": 0
    },
    "D1/04": {
        "start": 1676955600,
        "end": 0
    },
    "D1/05": {
        "start": 1676977200,
        "end": 0
    },
    "D1/06": {
        "start": 1676977200,
        "end": 0
    },
    "D1/07": {
        "start": 1677020400,
        "end": 0
    },
    "D1/08": {
        "start": 1677020400,
        "end": 0
    },
    "D1/09": {
        "start": 1677042000,
        "end": 0
    },
    "D1/10": {
        "start": 1677042000,
        "end": 0
    },
    "D1/11": {
        "start": 1677063600,
        "end": 0
    },
    "D1/12": {
        "start": 1677063600,
        "end": 0
    }
}


class PE:
    def __init__(self,
                 session: aiohttp.ClientSession,
                 username: str = '',
                 password: str = '',
                 local=None
                 ):
        """
        :param session: 进程
        :param username: 用户名
        :param password: 用户密码
        :param local: 本地持久化数据
        """
        self.session = session
        self.username = username
        self.password = password
        self.is_login = False

        if local:
            # 持久化数据只需要这两个 Cookies
            self.is_login = True
            self.session.cookie_jar.update_cookies({
                "MoodleSession": local["cookies"]["moodle_session"],
                "MOODLEID1_": local["cookies"]["moodle_id"]
            })
            self.sessKey = local["sessKey"]
        else:
            local = {
                "username": self.username,
                "sessKey": "None",
                "cookies": {
                    "moodle_session": "",
                    "moodle_id": ""
                },
                "course_list": [],
                "key": 0,
            }
        self.local = local

    @staticmethod
    def log_debug(cls, r):
        """
        调试用
        :param cls:
        :param r:
        :return:
        """
        print(f"\033[34m[INFO]\033[0m: {r}")

    @staticmethod
    def log_info(cls, r):
        """
        输出日志用
        :param cls: 实例
        :param r: 实际打印内容
        :return:
        """
        print(f"\033[32m[INFO]\033[0m: {r}")

    @staticmethod
    def log_error(cls, r):
        """
        报错用
        :param cls: 实例
        :param r: 实际打印内容
        :return:
        """
        print(f"\033[31m[ERROR]\033[0m: {r}")

    @staticmethod
    def wait(cls, t: int):
        if t < 0:
            return
        for i in range(t, 0, -1):
            print(f"\033[32m[INFO]\033[0m: 脚本将在 {i} 秒后再次检查", end='\r')
            time.sleep(1)

    def save_local(self):
        with open(os.path.join(os.path.dirname(__file__), "session.json"), 'w') as f:
            json.dump(self.local, f)

    async def auth(self):
        if self.is_login:
            return
        async with self.session.post(
                url="https://peselection.xjtlu.edu.cn/login/index.php",
                data={
                    "username": self.username,
                    "password": self.password,
                    "rememberusername": 1,
                    "anchor": ""
                },
                allow_redirects=False  # should be 301 here
        ) as resp:
            try:
                self.local["cookies"]["moodle_session"] = resp.cookies.get('MoodleSession').value
                self.local["cookies"]["moodle_id"] = resp.cookies.get('MOODLEID1_').value
            except AttributeError:
                self.log_error(self, "您的密码错误, 程序将退出, 请您确保账号密码正确后再次运行.")
                exit(1)
            # We don't need to test session, ffffff
            # Location should be like this: https://peselection.xjtlu.edu.cn/login/index.php?testsession=fffff
            # location = resp.headers.get("Location")

        async with self.session.get(
                url="https://peselection.xjtlu.edu.cn/my/",
        ) as resp:
            text = await resp.text()
        sessKey = sessKeyPattern.findall(text)[0]
        if not sessKey:
            self.log_error(self, "未拿到sessKey, 请尝试重新运行程序")
            exit(1)
        else:
            self.sessKey = sessKey
            self.local["sessKey"] = sessKey
            self.save_local()

    async def _get_ture_link(self, link) -> str:
        async with self.session.get(url=link, allow_redirects=False) as resp:
            location = resp.headers.get("Location")
        if location:
            return location
        else:
            return ""  # a falsy

    async def _get_course_list(self):
        """
        获取课程列表, 理论上一个人会被固定一个课程
        :return:
        """
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
            try:
                m = title.strip()[-5:]
                start = timeline[m]["start"]
            except:
                start = 0
                self.log_error(self, "未找到您课程的抢课开始时间, 请求提交将会即刻开始")
            course_list[cid] = {
                "link": link,
                "title": title,
                "start": start,
                "true_link": await self._get_ture_link(link)
            }
        # self.local["course_list"] = course_list
        return course_list

    async def _get_options(self, course_link):
        """
        获取指定课程的所以选项
        :param course_link: 课程链接
        :return:
        """
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

    async def _submit_choice(self, course, answer):
        """
        提交你你选择的选项
        :param id: 课程 ID
        :param answer: 选项 ID
        :return:
        """
        course_id = parse.parse_qs(parse.urlparse(course["true_link"]).query)["id"][0]
        print(self.sessKey)
        async with self.session.post(
                url="https://peselection.xjtlu.edu.cn/mod/choice/view.php",
                data={
                    "answer": answer,
                    "sesskey": self.sessKey,
                    "action": "makechoice",
                    "id": str(course_id)
                },
                allow_redirects=False
        ) as resp:
            # 由于目前没有得到具体的输出, 暂时无法判断正确的返回
            text = await resp.text()
            status_code = resp.status
        text = bs(text, 'html.parser')
        text = text.find('div', attrs={'id': 'page-content'}).get_text().strip()
        if "Invalid course module IDMore" in text:
            self.log_error(self, f"ID 获取有误, 回复状态码为{status_code}")
        elif "Sorry, this activity is not available until" in text:
            self.log_info(self, f"提交成功, 课程当前尚未开放, 回复状态码为{status_code}")
        else:
            self.log_info(self, f"提交, 结果并未出现在脚本预期中, 回复状态码为{status_code}, 原始返回数据为{text}")

    async def choice(self):
        """
        实际运行的函数, 所有选择的过程中, 在进行认证后直接运行这个即可
        :return:
        """
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

        key1, key2 = None, None
        while not key1:
            key = input("请输入您的第一志愿序号: ")
            if key in option_list.keys():
                key1 = key
            else:
                self.log_error(self, "输入的序号有误, 请您参照上方列表")
                continue
        while not key2:
            key = input("请输入您的第二序号: ")
            if key in option_list.keys():
                key2 = key
            else:
                self.log_error(self, "输入的序号有误, 请您参照上方列表")
                continue

        self.log_info(self, f"您的选择是\n第一志愿: {option_list[key1]['name']}\n第二志愿: {option_list[key2]['name']}")

        while 1:
            ddl = datetime.fromtimestamp(course["start"])
            now = datetime.now()
            delta = (ddl - now).seconds
            left_hour = int(delta / 3600)
            if left_hour > 0:
                self.log_info(self, f"距离抢课开始时间还有 {delta} 秒, 我们建议您 {left_hour} 个小时后再来运行脚本")
                self.wait(self, 3600)
                continue
            left_min = int(delta / 60)
            self.log_info(self, f"距离抢课开始时间还有 {left_min} 分钟, 脚本会在开抢 5 分钟开始提交")
            if left_min < 6:
                break
            self.wait(self, 60)
        num = 0
        num2 = 0
        while 1:
            num += 1
            delta = (datetime.fromtimestamp(course["start"]) - datetime.now()).seconds

            if delta < 0:
                num2 += 1

            if num2 < 10:
                self.log_info(self, num)
                await self._submit_choice(course, key1)
            else:
                self.log_info(self, num)
                await self._submit_choice(course, key2)


async def main(local=None, *args, **kwargs):
    async with aiohttp.ClientSession(headers={"User-Agent": ua}) as session:
        app = PE(session, local=local, *args, **kwargs)
        await app.auth()
        await app.choice()


if __name__ == '__main__':
    try:
        import asyncio

        print(""" 
      ___   _        _      __   __                       ___   ___ 
     | _ \ (_)  __  | |__   \ \ / /  ___   _  _   _ _    | _ \ | __|
     |  _/ | | / _| | / /    \ V /  / _ \ | || | | '_|   |  _/ | _| 
     |_|   |_| \__| |_\_\     |_|   \___/  \_,_| |_|     |_|   |___|
                                                                                                                       
    Github: https://github.com/AprilNEA/pick-your-pe
    License: GPL-3.0 (\033[32m本脚本基于GPL-3.0开源且免费\033[0m)
    Author: AprilNEA (https://sku.moe)
    Email: github@sku.moe
    """)

        local_path = os.path.join(os.path.dirname(__file__), "session.json")

        if os.path.exists(local_path):
            print(f"检测到本地文件{local_path}\n")
            with open(local_path, 'r') as f:
                local_files = json.load(f)
            asyncio.run(main(local=local_files))

        else:
            print(f"⚠️ 我们既不会保存更不会上传您的账号密码⚠️")
            u = input("请输入您的账户: ")
            p = getpass("请输入您的密码(密码不会显示,默念继续输就行): ")
            asyncio.run(main(None, u, p))

    except KeyboardInterrupt:
        print("\n")
        PE.log_info(None, "感谢使用.")
    except ClientConnectorCertificateError:
        print("\n")
        PE.log_error(None, "网络错误, SSL 认证错误")
        PE.log_info(None, "请检查你的 Python 版本(需要3.7.5^)或关闭魔法网络 (#^.^#)")
    except ClientError:
        print("\n")
        PE.log_error(None, "网络连接错误")
