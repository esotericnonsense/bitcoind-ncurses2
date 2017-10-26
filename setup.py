from setuptools import find_packages, setup

setup(
    name='bitcoindncurses2',
    version='0.3.1',
    author='Daniel Edgecumbe',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'console_scripts': ['bitcoind-ncurses2 = bitcoindncurses2.main:mainfn']
    })
