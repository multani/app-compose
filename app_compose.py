#!/usr/bin/env python3

import asyncio
import itertools
import os
import os.path
import shlex
import types

import click
import colorama
import yaml
import related



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
@click.option("-f", "--file", default="app-compose.yml", type=click.Path(exists=True))
@click.pass_context
def cli(ctx, file):
    colorama.init()
    ctx.obj.config_file = file


@cli.command()
@click.pass_context
def up(ctx):
    loop = asyncio.get_event_loop()
    composer = Composer(ctx.obj.config_file, loop=loop)
    loop.run_until_complete(composer.run())


def makedirs(path):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


class Composer:
    def __init__(self, config_file, *, loop):
        self.loop = loop
        self.config_file = config_file

        self.project_dir = os.path.dirname(os.path.realpath(config_file))

        self.work_dir = os.path.join(self.project_dir, ".app-compose")
        self.pids_dir = os.path.join(self.work_dir, "pids")

        makedirs(self.work_dir)
        makedirs(self.pids_dir)

    def read_config(self):

        @related.immutable
        class Service:
            name        = related.StringField()
            command     = related.StringField(required=True)
            cwd         = related.StringField(default=self.project_dir)
            environment = related.ChildField(dict, default={})

        @related.immutable
        class Services:
            services = related.MappingField(Service, "name")

        with open(self.config_file) as fp:
            config = related.from_yaml(fp, Services)

        return config

    def run(self):
        config = self.read_config()
        palette = Palette()

        tasks = []
        for i, (name, service) in enumerate(config.services.items()):
            app = self.create_service(service, palette.next_nice())
            tasks.append(app)

        return asyncio.gather(*tasks)

    async def create_service(self, service, color):
        exit_event = asyncio.Event()
        args = shlex.split(service.command)
        transport, protocol = await self.loop.subprocess_exec(
            lambda: ProcessOutputProtocol(service.name, color, exit_event),
            *args,
            cwd=service.cwd,
            stdin=None,
            env=service.environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        with open(os.path.join(self.pids_dir, service.name), "w") as fp:
            fp.write(str(transport.get_pid()))

        await exit_event.wait()
        transport.close()


def main():
    cli(auto_envvar_prefix='AC', obj=types.SimpleNamespace())


if __name__ == '__main__':
    main()
