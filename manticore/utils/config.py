"""
This file implements a configuration system.

The config values and constant are gathered from three sources:

    1. default values provided at time of definition
    2. yml files (i.e. ./manticore.yml)
    3. command line arguments

in that order of priority.
"""

import ast
import yaml
import io
import logging
import os
import sys

from itertools import product


_groups = {}


logger = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


class _var:
    def __init__(self, name: str='', default=None, description: str=None, defined: bool=True):
        self.name = name
        self.description = description
        self.value = default
        self.default = default
        self.defined = defined

    @property
    def was_set(self) -> bool:
        return self.value is not self.default


class _group:
    def __init__(self, name: str):
        # To bypass __setattr__
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, '_vars', {})

    def add(self, name: str, default=None, description: str=None):
        """
        Add a variable named |name| to this value group, optionally giving it a
        default value and a description.

        Variables must be added with this method before they can be set or read.
        Reading a variable replaces the variable that was defined previously, but
        updates the description if a new one is set.

        """
        if name in self._vars:
            raise ConfigError(f"{self.name}.{name} already defined.")

        v = _var(name, description=description, default=default)
        self._vars[name] = v

    def update(self, name: str, value=None, default=None, description: str=None):
        """
        Like add, but can tolerate existing values; also updates the value.

        Mostly used for setting fields from imported INI files and modified CLI flags.
        In the above case, we set defined to False so that they're not printed when
        describe_options() is called. That's desirable because we want describe_options
        to produce a list of everything that was defined in module headers, not values
        that were imported.
        """
        if name in self._vars:
            description = description or self._vars[name].description
            default = default or self._vars[name].default

        v = _var(name, description=description, default=default, defined=False)
        v.value = value
        self._vars[name] = v

    def get_description(self, name: str) -> str:
        """
        Return the description, or a help string of variable identified by |name|.
        """
        if name not in self._vars:
            raise ConfigError(f"{self.name}.{name} not defined.")

        return self._vars[name].description

    def updated_vars(self):
        """
        Return all vars that were explicitly set or updated with new values.
        """
        return filter(lambda x: x.was_set, self._vars.values())

    def _var_object(self, name: str) -> _var:
        return self._vars[name]

    def __getattr__(self, name):
        if name not in self._vars:
            raise AttributeError(f"Group '{self.name}' has no variable '{name}'")
        return self._vars[name].value

    def __setattr__(self, name, new_value):
        self._vars[name].value = new_value

    def __iter__(self):
        return iter(self._vars)

    def __contains__(self, key):
        return key in self._vars


def get_group(name: str):
    """
    Get a configuration variable group named |name|
    """
    global _groups

    if name in _groups:
        return _groups[name]

    group = _group(name)
    _groups[name] = group

    return group


def save(f):
    """
    Save current config state to an yml file stream identified by |f|

    :param f: where to write the config file
    """
    global _groups

    c = {}
    for group_name, group in _groups.items():
        section = dict((var.name, var.value) for var in group.updated_vars())
        if not section:
            continue
        c[group_name] = section

    yaml.safe_dump(c, f, line_break=True)


def parse_config(f):
    """
    Load an yml-formatted configuration from file stream |f|

    :param file f: Where to read the config.
    """

    try:
        c = yaml.safe_load(f)
        for section_name, section in c.items():
            group = get_group(section_name)

            for key, val in section.items():
                group.update(key)
                setattr(group, key, val)
    # Any exception here should trigger the warning; from not being able to parse yaml
    # to reading poorly formatted values
    except Exception:
        logger.error("Failed reading config file! Ignoring configuration. (Do you have a local [.]manticore.yml file?)")


def load_overrides(path=None):
    """
    Load config overrides from the yml file at |path|, or from default paths. If a path
    is provided and it does not exist, raise an exception

    Default paths: ./mcore.yml, ./.mcore.yml, ./manticore.yml, ./.manticore.yml.
    """

    if path is not None:
        names = [path]
    else:
        possible_names = ['mcore.yml', 'manticore.yml']
        names = [os.path.join('.', ''.join(x)) for x in product(['', '.'], possible_names)]

    for name in names:
        try:
            with open(name, 'r') as yml_f:
                logger.info(f'Reading configuration from {name}')
                parse_config(yml_f)
            break
        except FileNotFoundError:
            pass
    else:
        if path is not None:
            raise FileNotFoundError(f"'{path}' not found for config overrides")


def add_config_vars_to_argparse(args):
    """
    Import all defined config vars into |args|, for parsing command line.
    :param args: A container for argparse vars
    :type args: argparse.ArgumentParser or argparse._ArgumentGroup
    :return:
    """
    global _groups
    for group_name, group in _groups.items():
        for key in group:
            obj = group._var_object(key)
            args.add_argument(f"--{group_name}.{key}", type=type(obj.default),
                              default=obj.default, help=obj.description)


def get_config_keys():
    """
    Return an iterable covering all defined keys so far
    """
    global _groups
    for group_name, group in _groups.items():
        for key in group:
            yield f"{group_name}.{key}"


def describe_options():
    """
    Print a summary of variables that have been defined to be settable.
    """
    global _groups

    s = io.StringIO()

    for group_name, group in _groups.items():
        for key in group:
            obj = group._var_object(key)
            if not obj.defined:
                continue
            s.write(f"{group_name}.{key}\n")
            s.write(f"  default: {obj.default}\n")
            s.write(f"  {obj.description}\n")

    return s.getvalue()