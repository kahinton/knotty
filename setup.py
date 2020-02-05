from setuptools import setup, find_packages

with open('README.md', 'r') as readme:
    long_desc = readme.read()

setup(name='knotty',
      version='0.0.1',
      description='Application Performance Monitoring Made Easy',
      packages=find_packages(exclude=('tests',)),
      author="Kyle Hinton",
      license="MIT",
      install_requires=['psutil', 'flask', 'requests', 'numpy'],
      long_description=long_desc,
      long_description_content_type='text/markdown',
      python_requires='>=3.7'
      )
