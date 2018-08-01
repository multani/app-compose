#!/usr/bin/env python3

import asyncio
import itertools
import os

import click
import colorama
import yaml
import related


@related.immutable
class Service:
    name        = related.StringField()
    command     = related.StringField(required=True)
    cwd         = related.StringField(default=os.getcwd())
    environment = related.ChildField(dict, default={})


@related.immutable
class Services:
    services = related.MappingField(Service, "name")


class Color:
    def __init__(self, name, code):
        self.name = name
        self.code = code

        escape = "\033[{}{}m"

        self.color = escape.format(code, "")
        self.intense = escape.format(code, ";1")
        self.reset = escape.format(0, "")

    def __repr__(self):
        return "Color({!r}, {})".format(self.name, self.code)

    def paint(self, content, intense=False):
        return "{}{}{}".format(self.intense if intense else self.color,
            content, self.reset)


class Palette:
    def __init__(self):
        self.colors = {}

        for i, name in enumerate(['grey', 'red', 'green', 'yellow', 'blue',
            'magenta', 'cyan', 'white']):
            self.colors[name] = Color(name, 30 + i)

        self.nice = ['cyan', 'yellow', 'green', 'magenta', 'red', 'blue']
        self.counter = itertools.count()

    def next_nice(self):
        i = next(self.counter)
        name = self.nice[i % len(self.nice)]
        return self.colors[name]



class ProcessOutputProtocol(asyncio.SubprocessProtocol):
    def __init__(self, name, color, exit_event):
        self.buffer = []
        self.name = name
        self.color = color
        self.exit_event = exit_event

    def print(self, data):
        line = "{}: {}".format(
            self.color.paint(self.name, True),
            self.color.paint(data),
        )
        print(line)

    def pipe_data_received(self, fd, data):
        line = data.decode('utf-8')

        parts = line.split('\n')
        while len(parts) > 1:
            part = parts.pop(0)
            self.buffer.append(part)
            self.print("".join(self.buffer))
            self.buffer = []

        self.buffer.append(parts[0])

    def process_exited(self):
        self.exit_event.set()


@click.group()
def cli():
    colorama.init()


@cli.command()
def up():
    with open('app-compose.yml') as fp:
        config = related.from_yaml(fp, Services)

    loop = asyncio.get_event_loop()
    palette = Palette()

    tasks = []
    for i, (name, service) in enumerate(config.services.items()):
        app = create_service(loop, service, palette.next_nice())
        tasks.append(app)

    loop.run_until_complete(asyncio.gather(*tasks))


async def create_service(loop, service, color):
    exit_event = asyncio.Event()
    transport, protocol = await loop.subprocess_shell(
        lambda: ProcessOutputProtocol(service.name, color, exit_event),
        cmd=service.command,
        cwd=service.cwd,
        stdin=None,
        env=service.environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    await exit_event.wait()
    transport.close()


def main():
    cli(auto_envvar_prefix='AC')


if __name__ == '__main__':
    main()
