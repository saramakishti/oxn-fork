from setuptools import setup
setup(
    package_data={
        'oxn': ['schemas/*.json'],
    },
    include_package_data=True,
)