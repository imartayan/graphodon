from asyncio import gather
from asyncio_throttle import Throttler
import aiohttp
import json


class Instance:
    def __init__(self, domain, debug=False):
        self.domain = domain
        self._base_url = "https://" + domain
        self.debug = debug
        self.user_count = None
        self.users = {}
        self._session = None
        self._handle_session = False
        self._throttler = Throttler(
            rate_limit=300, period=300, retry_interval=1
        )  # https://docs.joinmastodon.org/api/rate-limits/

    def from_json(filename):
        with open(filename, "r") as file:
            data = json.load(file)
            instance = Instance(data["domain"])
            instance.user_count = data["user_count"]
            instance.users = data["users"]
            return instance

    def export_json(self, filename):
        with open(filename, "w+") as file:
            data = {
                "domain": self.domain,
                "user_count": self.user_count,
                "users": self.users,
            }
            json.dump(data, file)

    def _endpoint(self, endpoint):
        if self._session is None or self._session._base_url is None:
            return self._base_url + endpoint
        return endpoint

    def _init_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(base_url=self._base_url)
            self._handle_session = True

    async def _close_session(self):
        if self._handle_session:
            await self._session.close()
            self._session = None

    def _handle_error(self, response):
        print(f"({response.url}) error {response.status}")
        response.raise_for_status()

    async def _get_info(self):
        """
        https://docs.joinmastodon.org/methods/instance/#v1
        """
        if self.debug:
            print(f"({self.domain}) get info")
        url = self._endpoint("/api/v1/instance")
        async with self._throttler:
            async with self._session.get(url=url) as response:
                if "X-RateLimit-Limit" in response.headers:
                    rate_limit = int(response.headers["X-RateLimit-Limit"])
                    self._throttler.rate_limit = rate_limit
                if response.ok:
                    data = await response.text(encoding="utf-8")
                    info = json.loads(data)
                    self.user_count = int(info["stats"]["user_count"])
                else:
                    self._handle_error(response)

    async def _get_directory(self, offset, maxsize=80):
        """
        https://docs.joinmastodon.org/methods/directory/#get
        """
        if self.debug:
            print(f"({self.domain}) get dir {offset}")
        url = self._endpoint("/api/v1/directory")
        params = {"offset": offset, "limit": maxsize, "order": "new", "local": "true"}
        async with self._throttler:
            async with self._session.get(url=url, params=params) as response:
                if response.ok:
                    data = await response.text(encoding="utf-8")
                    users = json.loads(data)
                    if len(users) > 0:
                        for user in users:
                            username = user["username"] + "@" + self.domain
                            if username not in self.users:
                                keys = ["id", "followers_count", "following_count"]
                                self.users[username] = {k: user[k] for k in keys}
                else:
                    self._handle_error(response)

    async def _get_following(self, username, url=None, maxsize=80):
        """
        https://docs.joinmastodon.org/methods/accounts/#following
        """
        if self.debug:
            print(f"({self.domain}) get user {username}")
        user_id = self.users[username]["id"]
        if url is None:
            url = self._endpoint("/api/v1/accounts/" + user_id + "/following")
        params = {"limit": maxsize}
        async with self._throttler:
            async with self._session.get(url=url, params=params) as response:
                if response.ok:
                    data = await response.text(encoding="utf-8")
                    following = json.loads(data)
                    if len(following) > 0:
                        usernames = [
                            u["acct"]
                            if "@" in u["acct"]
                            else u["acct"] + "@" + self.domain
                            for u in following
                        ]
                        self.users[username]["following"] += usernames
                        if len(following) == maxsize:
                            pass
                else:
                    self._handle_error(response)

    async def fetch_users(self):
        self._init_session()
        await self._get_info()
        maxsize = 80
        await gather(
            *[
                self._get_directory(offset, maxsize)
                for offset in range(0, self.user_count, maxsize)
            ]
        )
        await self._close_session()

    async def build_graph(self):
        self._init_session()
        if self.users:
            usernames = [
                u
                for u, v in self.users.items()
                if v["following_count"] > 0 and "following" not in v
            ]
            for username in usernames:
                self.users[username]["following"] = []
            await gather(*[self._get_following(username) for username in usernames])
        await self._close_session()
