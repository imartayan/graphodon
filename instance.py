from asyncio import gather
from asyncio_throttle import Throttler
import aiohttp
import json


class Instance:
    def __init__(self, domain, build_graph=False, debug=False):
        self.domain = domain
        self.base_url = "https://" + domain
        self.build_graph = build_graph
        self.debug = debug
        self.user_count = None
        self.users = {}
        self.session = None
        self.handle_session = False
        self.throttler = Throttler(
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

    def endpoint(self, endpoint):
        if self.session is None or self.session._base_url is None:
            return self.base_url + endpoint
        return endpoint

    def init_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(base_url=self.base_url)
            self.handle_session = True

    async def close_session(self):
        if self.handle_session:
            await self.session.close()
            self.session = None

    def handle_error(self, response):
        print(f"Error {response.status} {response.reason} ({response.url})")
        response.raise_for_status()

    async def get_info(self):
        """
        https://docs.joinmastodon.org/methods/instance/#v1
        """
        if self.debug:
            print(f"({self.domain}) get info")
        url = self.endpoint("/api/v1/instance")
        async with self.throttler:
            async with self.session.get(url=url) as response:
                if "X-RateLimit-Limit" in response.headers:
                    rate_limit = int(response.headers["X-RateLimit-Limit"])
                    self.throttler.rate_limit = rate_limit
                if response.ok:
                    data = await response.text(encoding="utf-8")
                    info = json.loads(data)
                    self.user_count = int(info["stats"]["user_count"])
                else:
                    self.handle_error(response)

    async def get_directory(self, offset, maxsize=80):
        """
        https://docs.joinmastodon.org/methods/directory/#get
        """
        if self.debug:
            print(f"({self.domain}) get dir {offset}")
        url = self.endpoint("/api/v1/directory")
        params = {"offset": offset, "limit": maxsize, "order": "new", "local": "true"}
        async with self.throttler:
            async with self.session.get(url=url, params=params) as response:
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
                    self.handle_error(response)

    async def get_following(self, username, url=None, maxsize=80):
        """
        https://docs.joinmastodon.org/methods/accounts/#following
        """
        if self.debug:
            print(f"({self.domain}) get user {username}")
        user_id = self.users[username]["id"]
        if url is None:
            url = self.endpoint("/api/v1/accounts/" + user_id + "/following")
        params = {"limit": maxsize}
        async with self.throttler:
            async with self.session.get(url=url, params=params) as response:
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
                    self.handle_error(response)

    async def collect(self):
        self.init_session()
        await self.get_info()
        if self.debug:
            print(
                f"{self.domain}: {self.user_count} users, rate={self.throttler.rate_limit}"
            )
        maxsize = 80
        await gather(
            *[
                self.get_directory(offset, maxsize)
                for offset in range(0, self.user_count, maxsize)
            ]
        )
        if self.build_graph:
            usernames = [u for u, v in self.users.items() if v["following_count"] > 0]
            for username in usernames:
                self.users[username]["following"] = []
            await gather(*[self.get_following(username) for username in usernames])
        await self.close_session()
