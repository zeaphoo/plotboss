import os
import sys
import re
import ast
from setuptools import setup, find_packages
_version_re = re.compile(r'__version__\s+=\s+(.*)')

# example: 1.0b5.dev225
def main():
    with open('plotboss/__init__.py', 'rb') as f:
        version = str(ast.literal_eval(_version_re.search(
            f.read().decode('utf-8')).group(1)))

    print(str(version))


if __name__ == "__main__":
    main()