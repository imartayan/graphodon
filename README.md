# graphodon

This project aims to reconstruct the graph of [Mastodon](https://joinmastodon.org/) users using the [API](https://docs.joinmastodon.org/methods/).

## Requirements

This project requires Python 3.6+ (for `asyncio` support), [`aiohttp`](https://docs.aiohttp.org/en/stable/) to make asynchronous HTTP requests and [`asyncio-throttle`](https://github.com/hallazzang/asyncio-throttle) to limit the request rate.
These libraries can be installed using
```sh
pip install aiohttp aiodns asyncio-throttle
```

## Limitations

## Roadmap

- [x] Collect the public profiles of an instance
    - [x] Get the number of users
    - [x] Send requests asynchronously
    - [x] Respect the limit rate of the server
- [-] Collect the subscriptions of a user
    - [ ] Send multiple requests when the number of subscription is too big for a single request
    - [ ] Handle authorization tokens
- [ ] Construct the graphs of multiple instances
    - [ ] Collect instances addresses
    - [ ] Handle offline/private instances
    - [ ] Use multiple threads
    - [ ] Merge the graphs
- [ ] Provide a visualization tool
