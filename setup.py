import re
import ast
from setuptools import setup, find_packages

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('plotboss/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

with open('README.md', 'rb') as f:
    long_description = f.read().decode('utf-8')

packages = ['plotboss']
packages.extend(map(lambda x: 'plotboss.{}'.format(x), find_packages('plotboss')))

setup(
    name='plotboss',
    version=version,
    url='https://github.com/zeaphoo/plotboss/',
    license='MIT',
    author='Wei Zhuo',
    author_email='zeaphoo@qq.com',
    description='Chia network plot manager, auto plot manager, plot like a boss',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=packages,
    package_data={"plotboss":["settings.toml"]},
    include_package_data=False,
    zip_safe=False,
    platforms='any',
    install_requires=['basepy>=0.3.4', 'psutil', 'pendulum', 'asciimatics', 'loguru'],
    extras_require={
        'test': [
            'pytest>=3',
        ],
    },
    entry_points = {
        'console_scripts': ['plotboss=plotboss.plotboss:main'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    python_requires='>=3.7',
)
