"""Setup script for the aio_net_events package."""

from glob import glob
from os.path import abspath, basename, dirname, join, splitext
from setuptools import setup, find_packages

requires = [
    "anyio>=1.2.0",
    "async-generator>=1.10",
    "netifaces>=0.10.9"
]

extras_require = {
    "dev": [
        "curio>=0.9",
        "pytest>=5.2.4",
        "pytest-cov>=2.0.1",
        "trio>=0.13.0",
        "twine",
    ]
}

this_directory = abspath(dirname(__file__))

__version__ = None
exec(open(join(this_directory, "src", "aio_net_events", "version.py")).read())

with open(join(this_directory, "README.md")) as f:
    long_description = f.read()

setup(
    name="aio_net_events",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=__version__,
    author=u"Tam\u00e1s Nepusz",
    author_email="ntamas@gmail.com",
    url="https://github.com/ntamas/aio-net-events",
    packages=find_packages("src"),
    package_data={"aio_net_events": ["py.typed"]},
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    python_requires=">=3.5",
    install_requires=requires,
    extras_require=extras_require,
    test_suite="test",
)
