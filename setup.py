from setuptools import setup, find_packages

dev_requires = [
    'flake8',
    'pytest',
    'tox'
]

install_requires = [
    'requests',
    'click'
]

long_description = """
Template and share OpenSSH ssh_config(5) files.
A preprocessor for OpenSSH configurations.
Named for the favourite food of the Western Ground Parrot.
If you find this software useful, please consider donating to the effort to save this critically endangered species.

http://www.western-ground-parrot.org.au/
"""

setup(
    author="Grahame Bowland",
    author_email="grahame@angrygoats.net",
    description="Template and share OpenSSH ssh_config files.",
    long_description=long_description,
    license="GPL3",
    keywords="openssh ssh",
    url="https://github.com/grahame/sedge",
    name="sedge",
    version="2.0.2",
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    extras_require={
        'dev': dev_requires
    },
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'sedge = sedge.cli:cli',
        ],
    },
    package_data={'sedge': ['sedge_template.conf']},
    include_package_data=True,
)
