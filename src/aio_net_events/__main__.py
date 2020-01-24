from .task import NetworkEventDetector

from trio import run


async def main():
    detector = NetworkEventDetector()
    async for event in detector.events():
        print("{0!r}".format(event))


if __name__ == "__main__":
    run(main)
