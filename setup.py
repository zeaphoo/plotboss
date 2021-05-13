import re
import ast
from setuptools import setup, find_packages

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('plotbot/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

with open('README.md', 'rb') as f:
    long_description = f.read().decode('utf-8')

packages = ['plotbot']
packages.extend(map(lambda x: 'plotbot.{}'.format(x), find_packages('plotbot')))

setup(
    name='plotbot',
    version=version,
    url='https://github.com/zeaphoo/plotbot/',
    license='MIT',
    author='Wei Zhuo',
    author_email='zeaphoo@qq.com',
    description='Chia network plot manager, auto plot manager',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=packages,
    include_package_data=False,
    zip_safe=False,
    platforms='any',
    install_requires=['basepy', 'psutil', 'pendulum', 'texttable'],
    extras_require={
        'test': [
            'pytest>=3',
            'pyfakefs'
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    python_requires='>=3.6',
    entry_points='''
    '''
)
