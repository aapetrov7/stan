from setuptools import setup, find_packages

setup(
    name = 'stan',
    version = '0.1.0',
    description = "A bot to help with the deployment schedule at Anomali",
    url = 'https://github.com/jcomo/stan',
    author = 'Tony Petrov',
    author_email = 'apetrov@anomali.com',
    packages = find_packages(exclude=['docs', 'tests', 'scripts']),
    install_requires = ['six'],
    classifiers = [
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords = 'Shipbuilder bot'
)
