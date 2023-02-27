# graphodon

This project aims to reconstruct the social graph of [Mastodon](https://joinmastodon.org/) users using only the [Mastodon API](https://docs.joinmastodon.org/methods/).

## Requirements

This project requires Python 3.7+ (for `asyncio` support), [`aiohttp`](https://docs.aiohttp.org/en/stable/) to make asynchronous HTTP requests, [`aiofiles`](https://github.com/Tinche/aiofiles) for asynchronous file operations and [`asyncio-throttle`](https://github.com/hallazzang/asyncio-throttle) to limit the request rate.
These libraries can be installed using:
```sh
pip install aiohttp aiodns aiofiles asyncio-throttle
```

## Structure

- `instance.py` contains methods to collect the public profiles from a particular instance, and collect their subscriptions
- `federation.py` contains methods to get known instance domains, reconstruct the graphs from these instances and merge them

## Usage

Here is a minimal example to reconstruct the social graph of all known instances (beware, this takes a very long time!):
```py
from asyncio import run
from federation import Federation

if __name__ == "__main__":
    fed = Federation()
    run(fed.load_domains())
    fed.merge_all()
```

And here is a more elaborate example to reconstruct the social graph of instances of size 80, while caching the results in the `cache` folder and displaying debug informations:
```py
from asyncio import run
from federation import Federation

if __name__ == "__main__":
    fed = Federation(cache="cache", debug=True)
    run(fed.load_domains())
    domains = [domain for domain, count in fed.domains.items() if count == 80]
    fed.fetch(domains)
    fed.merge_all()
```

The results can then be loaded from the cache only:
```py
from asyncio import run
from federation import Federation

if __name__ == "__main__":
    fed = Federation(cache="cache")
    run(fed.load_domains())
    fed.merge_all(cache_only=True)
```

## Limitations

- We can only collect [discoverable](https://docs.joinmastodon.org/entities/Account/#discoverable) accounts, so the graph we obtain is only partial.
- Due to [rate limits](https://docs.joinmastodon.org/api/rate-limits/), Mastodon servers only accept up to 300 requests within 5 minutes from a given IP. This makes the reconstruction of large instances considerably slower.

## Roadmap

- [x] Collect the public profiles of an instance
    - [x] Get the number of users
    - [x] Send requests asynchronously
    - [x] Respect the limit rate of the server
- [x] Collect the subscriptions of a user
    - [x] Send multiple requests when the number of subscriptions is too big for a single request
- [x] Reconstruct the graphs of multiple instances
    - [x] Collect instances addresses
    - [x] Use multiple threads
    - [x] Handle unreachable instances
    - [x] Cache the reconstructed graphs
    - [x] Merge the graphs
- [x] Provide a visualization tool
