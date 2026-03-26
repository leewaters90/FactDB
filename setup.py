from setuptools import setup, find_packages

setup(
    name="factdb",
    version="0.1.0",
    description="Engineering fact database with verification, change management, and reasoning engine",
    author="FactDB Contributors",
    python_requires=">=3.10",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "sqlalchemy>=2.0.0",
        "alembic>=1.13.0",
        "click>=8.1.0",
        "tabulate>=0.9.0",
        "python-dateutil>=2.8.0",
        "flask>=3.0.0",
    ],
    extras_require={
        "dev": ["pytest>=7.4.0", "pytest-cov>=4.1.0"],
    },
    entry_points={
        "console_scripts": [
            "factdb=factdb.cli:cli",
        ],
    },
)
