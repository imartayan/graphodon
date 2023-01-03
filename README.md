# graphodon

This project aims to reconstruct the graph of [Mastodon](https://joinmastodon.org/) users using only the [API](https://docs.joinmastodon.org/methods/).

## Requirements

This project requires Python 3.7+ (for `asyncio` support), [`aiohttp`](https://docs.aiohttp.org/en/stable/) to make asynchronous HTTP requests, [`aiofiles`](https://github.com/Tinche/aiofiles) for asynchronous file operations and [`asyncio-throttle`](https://github.com/hallazzang/asyncio-throttle) to limit the request rate.
These libraries can be installed using:
```sh
pip install aiohttp aiodns asyncio-throttle
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
    - [ ] Send multiple requests when the number of subscriptions is too big for a single request
    - [ ] Handle authorization tokens
- [x] Reconstruct the graphs of multiple instances
    - [x] Collect instances addresses
    - [x] Use multiple threads
    - [ ] Handle unreachable instances
    - [ ] Merge the graphs
- [ ] Provide a visualization tool
