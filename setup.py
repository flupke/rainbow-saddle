#!/usr/bin/env python
from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()


version = '0.2'

install_requires = [
    'psutil==0.6.1',
]


setup(name='rainbow-saddle',
    version=version,
    description="A wrapper around gunicorn to handle graceful restarts correctly",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords='gunicorn wrapper graceful restart',
    author='Luper Rouch',
    author_email='luper.rouch@gmail.com',
    url='https://github.com/flupke/rainbow-saddle',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'console_scripts':
            ['rainbow-saddle=rainbowsaddle:main']
    }
)
