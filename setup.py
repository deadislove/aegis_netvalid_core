import os
from setuptools import setup, find_packages

_here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_here, "requirements.txt"), encoding="utf-8") as f:
    install_requires = [
        line.strip() for line in f
        if line.strip() and not line.strip().startswith("#")
    ]

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
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'aegis=main_aegis:main',
        ],
    },
    python_requires='>=3.10',
)