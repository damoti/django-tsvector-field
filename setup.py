#!/usr/bin/env python
import os
from setuptools import setup


BASE = os.path.dirname(__file__)
README_PATH = os.path.join(BASE, 'README.rst')
CHANGES_PATH = os.path.join(BASE, 'CHANGES.rst')
long_description = '\n\n'.join((
    open(README_PATH).read(),
    open(CHANGES_PATH).read(),
))


setup(
    name='django-tsvector-field',
    version='0.9.5',
    url='https://github.com/damoti/django-tsvector-field',
    license='BSD',
    description='Django field implementation for PostgreSQL tsvector.',
    long_description=long_description,
    author='Lex Berezhny',
    author_email='lex@damoti.com',
    keywords='django,postgres',
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=['tsvector_field'],
)
