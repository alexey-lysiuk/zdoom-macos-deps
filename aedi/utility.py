#
#    Helper module to build macOS version of various source ports
#    Copyright (C) 2020-2021 Alexey Lysiuk
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import collections.abc
from distutils.version import StrictVersion
import os
from pathlib import Path
import shutil


# Minimum OS versions
OS_VERSION_X86_64 = StrictVersion('10.9')
OS_VERSION_ARM64 = StrictVersion('11.0')


class CommandLineOptions(dict):
    # Rules to combine argument's name and value
    MAKE_RULES = 0
    CMAKE_RULES = 1

    def to_list(self, rules=MAKE_RULES) -> list:
        result = []

        for arg_name, arg_value in self.items():
            if rules == CommandLineOptions.MAKE_RULES:
                option = arg_name + ('=' + arg_value if arg_value else '')
            elif rules == CommandLineOptions.CMAKE_RULES:
                arg_value = arg_value if arg_value else ''
                option = f'-D{arg_name}={arg_value}'
            else:
                assert False, 'Unknown argument rules'

            result.append(option)

        return result


class TargetPlatform:
    def __init__(self, architecture: str, host: str, os_version: [str, StrictVersion],
                 sdk_path: Path, prefix_path: Path):
        self.architecture = architecture
        self.host = host
        self.os_version = os_version if isinstance(os_version, StrictVersion) else StrictVersion(os_version)
        self.sdk_path = sdk_path
        self.c_compiler = prefix_path / 'bin' / f'{host}-gcc'
        self.cxx_compiler = prefix_path / 'bin' / f'{host}-g++'


def symlink_directory(src_path: Path, dst_path: Path, cleanup=True):
    if cleanup:
        # Delete obsolete symbolic links
        for root, _, files in os.walk(dst_path, followlinks=True):
            for filename in files:
                file_path = root + os.sep + filename

                if os.path.islink(file_path) and not os.path.exists(file_path):
                    os.remove(file_path)

    # Create symbolic links if needed
    for entry in src_path.iterdir():
        dst_subpath = dst_path / entry.name
        if entry.is_dir():
            os.makedirs(dst_subpath, exist_ok=True)
            symlink_directory(entry, dst_subpath, cleanup=False)
        elif not dst_subpath.exists():
            if entry.is_symlink():
                shutil.copy(entry, dst_subpath, follow_symlinks=False)
            else:
                os.symlink(entry, dst_subpath)


# Case insensitive dictionary class from
# https://github.com/psf/requests/blob/v2.25.0/requests/structures.py

class CaseInsensitiveDict(collections.abc.MutableMapping):
    """A case-insensitive ``dict``-like object.
    Implements all methods and operations of
    ``MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.
    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive::
        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True
    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.
    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.
    """

    def __init__(self, data=None, **kwargs):
        self._store = collections.OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, collections.abc.Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))
