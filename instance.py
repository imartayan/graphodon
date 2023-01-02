from asyncio import gather
from asyncio_throttle import Throttler
import aiohttp
import json


class Instance:
    def __init__(self, domain, build_graph=False, debug=False):
        self.domain = domain
        self.session = None
        self.throttler = Throttler(
            rate_limit=300, period=300, retry_interval=1
        )  # https://docs.joinmastodon.org/api/rate-limits/
        self.build_graph = build_graph
        self.debug = debug
        self.user_count = None
        self.users = {}

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

    def handle_error(self, response):
        print(f"Error {response.status} {response.reason} ({response.url})")
        response.raise_for_status()

    async def get_info(self):
        url = "/api/v1/instance"
        async with self.throttler:
            async with self.session.get(url=url) as response:
                if "X-RateLimit-Limit" in response.headers:
                    rate_limit = int(response.headers["X-RateLimit-Limit"])
                    self.throttler.rate_limit = rate_limit
                if response.ok:
                    data = await response.text()
                    info = json.loads(data)
                    self.user_count = int(info["stats"]["user_count"])
                else:
                    self.handle_error(response)

    async def add_user(self, user):
        username = user["username"] + "@" + self.domain
        if username not in self.users:
            fields = ["id", "followers_count", "following_count"]
            self.users[username] = {f: user[f] for f in fields}

    async def get_directory(self, offset, limit=80):
        if self.debug:
            print("get dir", offset)
        url = "/api/v1/directory"
        params = {"offset": offset, "limit": limit, "order": "new", "local": "true"}
        async with self.throttler:
            async with self.session.get(url=url, params=params) as response:
                if response.ok:
                    data = await response.text()
                    users = json.loads(data)
                    if len(users) > 0:
                        await gather(*[self.add_user(user) for user in users])
                else:
                    self.handle_error(response)

    async def add_following(self, username, following):
        usernames = [
            u["acct"] if "@" in u["acct"] else u["acct"] + "@" + self.domain
            for u in following
        ]
        self.users[username]["following"] += usernames

    async def get_following(self, username, limit=80):
        if self.debug:
            print("get user", username)
        user_id = self.users[username]["id"]
        url = "/api/v1/accounts/" + user_id + "/following"
        params = {"limit": limit}
        async with self.throttler:
            async with self.session.get(url=url, params=params) as response:
                if response.ok:
                    data = await response.text()
                    following = json.loads(data)
                    if len(following) > 0:
                        await gather(self.add_following(username, following))
                else:
                    self.handle_error(response)

    async def collect(self):
        self.session = aiohttp.ClientSession(base_url="https://" + self.domain)
        if self.user_count is None:
            await self.get_info()
        if self.debug:
            print("User count:", self.user_count)
            print("Rate limit:", self.throttler.rate_limit)
        limit = 80
        await gather(
            *[
                self.get_directory(offset, limit)
                for offset in range(0, self.user_count, limit)
            ]
        )
        if self.build_graph:
            usernames = [u for u, v in self.users.items() if v["following_count"] > 0]
            for username in usernames:
                self.users[username]["following"] = []
            await gather(*[self.get_following(username) for username in usernames])
        await self.session.close()
