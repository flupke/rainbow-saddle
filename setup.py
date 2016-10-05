#!/usr/bin/env python
from setuptools import setup, find_packages
import os


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()
version = '0.4.0'
install_requires = [
    'psutil>=4.2.0',
]


setup(
    name='rainbow-saddle',
    version=version,
    description=(
        'A wrapper around gunicorn to handle graceful restarts correctly'
    ),
    long_description=README + '\n\n' + NEWS,
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
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
