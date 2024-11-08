# -*- coding: utf-8 -*-
# SSO统一认证登录接口
import asyncio
import logging
from typing import Optional

import httpx

from . import patterns
from .exceptions import LoginError
from config import config


class SsoApi:

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._session: Optional[httpx.AsyncClient] = None
        self._url = ''

    async def __get_execution(self):
        # 原有的获取execution的方法已经失效，似乎是因为现在采用的是JS重定向，所以需要手动获取
        # 因为self._url = https://bykc.buaa.edu.cn/system/home
        # 这里sso的载荷里是另一个url，因此不再根据self._url生成，此函数请避免其他地方调用
        redirect_url = "https://sso.buaa.edu.cn/login?noAutoRedirect=true&service=https%3A%2F%2Fbykc.buaa.edu.cn%2Fsscv%2Fcas%2Flogin"
        resp = await self._session.get(redirect_url)
        result = patterns.execution.search(resp.text)
        assert result, 'unexpected behavior: execution code not retrieved'
        return result.group(1)

        # resp = await self._session.get(self._url, follow_redirects=True)
        # result = patterns.execution.search(resp.text)
        # assert result, 'unexpected behavior: execution code not retrieved'
        # return result.group(1)

    async def __get_login_form(self):
        return {
            'username': self._username,
            'password': self._password,
            'submit': '登录',
            'type': 'username_password',
            'execution': await self.__get_execution(),
            '_eventId': 'submit',
        }

    async def login_sso(self, url):
        """
        北航统一认证接口
        :param url: 不同网站向sso发送自己的域名，此时sso即了解是那个网站和应该返回何种token
        :return: token的返回形式为一个带有ticket的url，一般访问这个url即可在cookies中或者storages中储存凭证
        不同的网站有不同的处理形式
        """
        self._url = url
        try:
            async with httpx.AsyncClient() as self._session:
                self._session.headers['User-Agent'] = config.get('user_agent')
                login_form = await self.__get_login_form()
                resp = await self._session.post('https://sso.buaa.edu.cn/login', data=login_form, follow_redirects=False)
                if resp.status_code != 302:
                    raise LoginError('登录失败:账号密码错误')
                location = resp.headers['Location']
                logging.info('location: ' + location)
            return location
        except httpx.HTTPError:
            raise LoginError('登录失败:网络错误')


async def test():
    from config import config
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    sso = SsoApi(config.get('sso_username'), config.get('sso_password'))
    location = await sso.login_sso(
        'https://sso.buaa.edu.cn/login?TARGET=http%3A%2F%2Fbykc.buaa.edu.cn%2Fsscv%2FcasLogin')
    print(location)


if __name__ == '__main__':
    asyncio.run(test())
