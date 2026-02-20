"""Command registry — maps slash commands to handler functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from cli_mail.app import App

CommandHandler = Callable[["App", list[str]], None]


@dataclass
class Command:
    name: str
    handler: CommandHandler
    aliases: list[str]
    description: str


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._alias_map: dict[str, str] = {}

    def register(
        self,
        name: str,
        handler: CommandHandler,
        aliases: list[str] | None = None,
        description: str = "",
    ) -> None:
        cmd = Command(name=name, handler=handler, aliases=aliases or [], description=description)
        self._commands[name] = cmd
        for alias in cmd.aliases:
            self._alias_map[alias] = name

    def get(self, name: str) -> Command | None:
        if name in self._commands:
            return self._commands[name]
        canonical = self._alias_map.get(name)
        if canonical:
            return self._commands.get(canonical)
        return None

    @property
    def command_names(self) -> list[str]:
        names = list(self._commands.keys())
        names.extend(self._alias_map.keys())
        return sorted(names)

    @property
    def commands(self) -> list[Command]:
        return list(self._commands.values())
