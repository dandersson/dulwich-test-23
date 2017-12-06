#!/usr/bin/env python3
"""Push a Git branch using `dulwich`."""
# This script should be Python 2/3 compatible.
from __future__ import print_function

import argparse

import logging
import os
import sys

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

import dulwich.porcelain


logger = logging.getLogger(__name__)


class InvalidConfigError(Exception):
    """Raise when the given configuration is malformed."""


def eprint(message):
    """Print error message."""
    print('%s:' % sys.argv[0], 'error: %s' % message, file=sys.stderr)


def get_credentials(config_fp):
    """
    Return repository URL, username and API token from configuration file
    handle with format

        [Git repository]
        url = https://example.com/your-repo-url.git

        [Git credentials]
        username = your-username
        api_token = an-api-token-or-password

    Args:
        config_fp: file handle to configuration

    Returns:
        url, username, password

    Raises:
        InvalidConfigError in case the config file is malformed.
    """
    cparser = configparser.SafeConfigParser()
    cparser.readfp(config_fp)
    try:
        url = cparser.get('Git repository', 'url')
        username = cparser.get('Git credentials', 'username')
        password = cparser.get('Git credentials', 'api_token')
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.debug(e, exc_info=True)
        raise InvalidConfigError(e)

    if not (url.startswith('https://') or url.startswith('http://')):
        raise InvalidConfigError('invalid URL "%s" -- only the `http` and `https` protocols are supported')

    return url, username, password


def create_url(url, username, api_token):
    """Create URL with included credentials."""
    protocol, rest = url.split('//', 1)

    return '%s//%s@%s' % (protocol, ':'.join(quote(i) for i in (username, api_token)), rest)


def list_branches(repository):
    """List local and remote branches in given repository path."""
    with dulwich.porcelain.open_repo_closing(repository) as repo:
        local_branches = repo.refs.keys(base=b'refs/heads/')
        remote_branches = repo.refs.keys(base=b'refs/remotes/')

    logger.debug('Local branches:  %s', local_branches)
    logger.debug('Remote branches: %s', remote_branches)


def show_ls_remote(url):
    """Show `ls-remote` output for given repository URL."""
    logger.debug(dulwich.porcelain.ls_remote(url))


def push_branch(repository, url, branch):
    """Push given branch in given repository to given URL."""
    dulwich.porcelain.push(repository, url, refspecs=branch)


def parse_cli(args):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)

    def git_repo_path(path):
        """Raise `argparse` error if path is not an existing directory."""
        if not os.path.isdir(path):
            parser.error('%r is not a valid directory' % path)
        if not os.path.isdir(os.path.join(path, '.git')):
            parser.error('%r is not a Git repository' % path)
        return path

    parser.add_argument('repository', metavar='REPO', type=git_repo_path, help='path to local repository')
    parser.add_argument('branch', metavar='BRANCH', help='branch to push')
    parser.add_argument(
        '--config',
        metavar='CONFIG',
        type=argparse.FileType('r'),
        default=os.path.join(os.path.dirname(__file__), '.credentials'),
        help='configuration file (default: %(default)s)',
    )
    parser.add_argument('--debug', action='store_true', help='enable debugging output')

    return parser.parse_args(args)


def main(argv):
    """Push a Git branch using `dulwich`."""
    args = parse_cli(argv[1:])
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    logger.debug('CLI args: %r', args)

    with args.config as f:
        try:
            url, username, api_token = get_credentials(f)
        except InvalidConfigError as e:
            eprint('Given configuration was invalid: %s' % e)
            sys.exit(1)

    url_with_credentials = create_url(url, username, api_token)
    branch = bytes(args.branch, encoding='utf-8') if sys.version_info[0] >= 3 else args.branch

    if logger.isEnabledFor(logging.DEBUG):
        list_branches(args.repository)
        show_ls_remote(url_with_credentials)

    push_branch(args.repository, url_with_credentials, branch)


if __name__ == '__main__':
    main(sys.argv)
