from setuptools import setup, find_packages

setup(
    name="aegis-netvalid-core",
    version="1.0.0",
    author="Da-Wei Lin",
    description="Aegis NetValid Core - Network Security & Stress Tool CLI",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    py_modules=['main_aegis'],
    include_package_data=True,
    install_requires=[
        "rich",
        "scapy",
        "PyYAML",
        "boto3",
        "matplotlib",
        "pandas",
        "influxdb-client",
        "invoke",
        "paramiko",
        "psutil",
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'aegis=main_aegis:main',
        ],
    },
    python_requires='>=3.10',
)