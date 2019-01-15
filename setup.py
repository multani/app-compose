from setuptools import setup


args = dict(
    name="app-compose",
    version='0.0.2',
    entry_points=dict(
        console_scripts=[
            "ac=app_compose:main",
            "app-compose=app_compose:main",
        ],
    ),
    install_requires=[
        'click',
        'colorama',
        'pyyaml',
        'related',
    ]
)


if __name__ == '__main__':
    setup(**args)
