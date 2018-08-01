from setuptools import setup


args = dict(
    name="app-compose",
    version='0.0.1',
    entry_points=dict(
        console_scripts=[
            "ac=app_compose:main",
            "app-compose=app_compose:main",
        ],
    ),
    install_requires=[
        'click==6.7',
        'colorama==0.3.9',
        'pyyaml==3.13',
        'related==0.6.3',
    ]
)


if __name__ == '__main__':
    setup(**args)
