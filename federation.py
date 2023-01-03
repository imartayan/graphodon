from multiprocessing import cpu_count, Pool
from asyncio import gather, run, Semaphore
from pathlib import Path
import aiohttp
import json
from instance import Instance


class Federation:
    def __init__(self, cache=None, debug=False):
        if cache:
            self._cache = Path.cwd().joinpath(cache)
            self._cache.mkdir(parents=True, exist_ok=True)
        else:
            self._cache = None
        self._debug = debug
        self.domains = {}
        self.instances = {}
        self._tasks = []

    async def load_domains(self, filename=None):
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
            if not isinstance(user_count, int):
                continue
            if 10 <= user_count <= 20:
                self.domains[domain] = user_count
        if self._debug:
            print(f"{len(self.domains)} domains")

    async def _init_instance(self, semaphore, domain):
        if self._cache:
            file = self._cache.joinpath(domain + ".json")
            if file.exists():
                if self._debug:
                    print(f"{domain} in cache")
                async with semaphore:
                    self.instances[domain] = await Instance.from_json(file)
                return
        self.instances[domain] = Instance(domain, debug=self._debug)
        self._tasks.append(domain)

    async def _init_instances(self, domains, max_open=200):
        semaphore = Semaphore(max_open)
        await gather(*[self._init_instance(semaphore, domain) for domain in domains])

    async def _fetch_instance(self, session, domain):
        instance = self.instances[domain]
        instance._session = session
        try:
            await instance.fetch_users(create_session=False)
            if instance.users:
                await instance.build_graph(create_session=True)
                if self._cache:
                    await instance.export_json(self._cache.joinpath(domain + ".json"))
            if self._debug:
                print(f"{domain} fetched")
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

    def fetch_all(self):
        if not self.domains:
            run(self.load_domains())
        run(self._init_instances(self.domains.keys()))
        cpus = cpu_count()
        with Pool(processes=cpus) as pool:
            N = len(self._tasks)
            buckets = [
                self._tasks[i * N // cpus : (i + 1) * N // cpus] for i in range(cpus)
            ]
            pool.map(self._process_instances, buckets)
