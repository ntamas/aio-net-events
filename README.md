# aio-net-events

`aio-net-events` is a Python library that provides asynchronous generators
yielding events when the network configuration of the machine changes.
Currently only network interface additions / removals and IP address additions /
removals are supported; more events may be added later.

Supports Windows, Linux and macOS at the moment.

Requires Python >= 3.7.

Works with [`asyncio`](https://docs.python.org/3/library/asyncio.html) and
[`trio`](https://trio.readthedocs.io/en/stable/).

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install
`aio-net-events`.

```bash
pip install aio-net-events
```

## Usage

## Contributing

Pull requests are welcome. For major changes, please open an issue first to
discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
