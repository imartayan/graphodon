from multiprocessing import Pool, cpu_count
from asyncio import gather, run
import aiohttp
import json
from instance import Instance


class Federation:
    def __init__(self, cache=None, debug=False):
        self.cache = cache
        self.debug = debug
        self._catalog = {}
        self.instances = {}

    async def load_instance_list(self, filename=None):
        if filename:
            with open(filename, mode="r") as file:
                data = file.read()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url="https://instances.social/instances.json"
                ) as response:
                    if response.ok:
                        data = await response.text(encoding="utf-8")
                    else:
                        raise RuntimeError("Cannot fetch instance list")
        instances = json.loads(data)
        for instance in instances:
            if "name" not in instance or "users" not in instance:
                continue
            domain = instance["name"]
            user_count = instance["users"]
            if "@" in domain or "/" in domain:
                if self.debug:
                    print("Invalid domain", domain)
                continue
            if not isinstance(user_count, int):
                if self.debug:
                    print("Unknown user count", domain)
                continue
            if 12 <= user_count <= 12:
                self._catalog[domain] = user_count
        if self.debug:
            print(f"{len(self._catalog)} valid domains")

    async def _fetch_instance(self, session, domain):
        instance = self.instances[domain]
        instance._session = session
        try:
            await instance.fetch_users(create_session=False)
            await instance.build_graph()
            self.instances[domain] = instance
            if self.cache:
                await instance.export_json(self.cache + "/" + domain + ".json")
            print(domain, "done")
        except Exception:
            pass
        finally:
            instance._session = None

    async def _fetch_many_instances(self, domains):
        timeout = aiohttp.ClientTimeout(sock_connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            await gather(*[self._fetch_instance(session, domain) for domain in domains])

    def _process_instances(self, domains):
        run(self._fetch_many_instances(domains))

    def fetch_instances(self):
        tasks = []
        for domain in self._catalog:
            if self.cache:
                pass
            self.instances[domain] = Instance(domain, debug=self.debug)
            tasks.append(domain)
        cpus = cpu_count()
        with Pool(processes=cpus) as pool:
            N = len(tasks)
            buckets = [tasks[i * N // cpus : (i + 1) * N // cpus] for i in range(cpus)]
            pool.map(self._process_instances, buckets)
