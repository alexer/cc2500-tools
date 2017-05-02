#! /usr/bin/env python3
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

setup(
	name='CC2500-tools',
	version='0.1',
	description='Various tools for working with CC2500 wireless transceivers',
	author='Aleksi Torhamo',
	author_email='aleksi@torhamo.net',
	url='http://github.com/alexer/cc2500-tools',
	packages=['cc2500'],
)

