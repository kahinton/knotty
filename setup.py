from setuptools import setup, find_packages

with open('README.md', 'r') as readme:
    long_desc = readme.read()

setup(name='knotty',
      version='0.4.0',
      description='Application Performance Monitoring Made Easy',
      packages=find_packages(exclude=('tests', 'docs', )),
      author="Kyle Hinton",
      license="MIT",
      install_requires=['psutil', 'flask', 'requests', 'numpy'],
      long_description=long_desc,
      url="https://github.com/kahinton/knotty",
      long_description_content_type='text/markdown',
      python_requires='>=3.7'
      )
