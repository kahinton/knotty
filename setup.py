from setuptools import setup, find_packages

with open('README.md', 'r') as readme:
    long_desc = readme.read()

setup(name='knotty_old',
      version='0.0.1',
      description='Application Performance Monitoring Made Easy',
      packages=find_packages(exclude=('tests',)),
      author="Kyle Hinton",
      license="MIT",
      long_description=long_desc,
      long_description_content_type='text/markdown')
