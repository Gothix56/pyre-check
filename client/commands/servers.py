# Copyright (c) 2016-present, Facebook, Inc.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import functools
import json
import logging
from pathlib import Path
from typing import List, NamedTuple

from .. import LOG_DIRECTORY, find_project_root, log
from .command import JSON, Command
from .stop import Stop


LOG: logging.Logger = logging.getLogger(__name__)


ROOT_PLACEHOLDER_NAME = "<root>"
PID_MAXIMUM_WIDTH = 10


class ServerDetails(NamedTuple):
    local_root: str
    pid: int
    server_pid_path: Path

    @staticmethod
    def _from_server_path(
        server_pid_path: Path, dot_pyre_root: Path
    ) -> "ServerDetails":
        return ServerDetails(
            pid=int(server_pid_path.read_text()),
            server_pid_path=server_pid_path,
            local_root=str(server_pid_path.relative_to(dot_pyre_root).parent.parent),
        )


class Servers(Command):
    NAME: str = "servers"

    @classmethod
    def add_subparser(cls, parser: argparse._SubParsersAction) -> None:
        servers_parser = parser.add_parser(
            cls.NAME,
            epilog="""
            Command to manipulate multiple Pyre servers.
            """,
        )
        servers_parser.set_defaults(command=cls, noninteractive=True)
        subparsers = servers_parser.add_subparsers(dest="servers_subcommand")

        subparsers.add_parser("list", help="List running servers.")
        subparsers.add_parser("stop", help="Stop all running servers.")

    @staticmethod
    @functools.lru_cache()
    def _dot_pyre_root() -> Path:
        return Path(find_project_root(str(Path.cwd())), LOG_DIRECTORY)

    @staticmethod
    def _print_server_details(
        all_server_details: List[ServerDetails], output_format: str
    ) -> None:
        server_details = [
            {
                "pid": details.pid,
                "name": details.local_root
                if details.local_root != "."
                else ROOT_PLACEHOLDER_NAME,
            }
            for details in all_server_details
        ]
        if output_format == JSON:
            log.stdout.write(json.dumps(server_details))
        else:
            log.stdout.write("Pyre servers:\n<pid> <server-root>")
            for details in server_details:
                log.stdout.write(
                    "{:<{column_one_width}} {}".format(
                        details["pid"],
                        details["name"],
                        column_one_width=PID_MAXIMUM_WIDTH,
                    )
                )

    @staticmethod
    def _find_servers() -> List[Path]:
        return list(Servers._dot_pyre_root().glob("**/server.pid"))

    def _stop_servers(self, servers: List[ServerDetails]) -> None:
        for server in servers:
            Stop(
                arguments=self._arguments,
                original_directory=str(
                    self._dot_pyre_root().parent / server.local_root
                ),
            ).run()

    def _run(self) -> None:
        all_server_details = sorted(
            (
                ServerDetails._from_server_path(server_path, self._dot_pyre_root())
                for server_path in self._find_servers()
            ),
            key=lambda details: details.local_root,
        )

        subcommand = self._arguments.servers_subcommand
        if subcommand == "list" or subcommand is None:
            self._print_server_details(all_server_details, self._output)
        elif subcommand == "stop":
            self._stop_servers(all_server_details)
