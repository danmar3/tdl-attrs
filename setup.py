try:
    from pip._internal.operations import freeze
except ImportError:  # pip < 10.0
    from pip.operations import freeze
from setuptools import setup, find_packages
import importlib.util
# for development installation: pip install -e .
# for distribution: python setup.py sdist #bdist_wheel
#                   pip install dist/project_name.tar.gz

DEPS = ['networkx']
DEPS_DEV = ['pytest', 'coverage']


def get_dependencies():
    return DEPS


setup(name='tdl_attrs',
      version='0.0.1',
      packages=find_packages(
          exclude=["*test*", "tests"]),
      install_requires=get_dependencies(),
      extras_require={
          'dev': DEPS_DEV
      },
      licence='MIT',
      )
