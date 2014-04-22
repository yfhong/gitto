import argparse
import os.path
import os
import re
import sys
import ConfigParser

from .command import Command, argument


DATADIR = os.environ.get("GITTO_DATADIR", "data")
CONFDIR = ".config"
USER = os.environ.get("GITTO_USER", None)


NAME_RE = re.compile(r'[a-z0-9_][a-z0-9\.\-_]*')
GIT_DAEMON_EXPORT_OK = "git-daemon-export-ok"


def check_acl(basedir, perm):
    config = ConfigParser.SafeConfigParser(allow_no_value=True)

    try:
        f = open(os.path.join(basedir, CONFDIR, "acl.conf"), "r")
    except IOError:
        return False

    with f:
        try:
            config.readfp(f)
        except ConfigParser.Error:
            return False

    try:
        users = [u for u,_ in config.items(perm)]
    except ConfigParser.NoSectionError:
        return False

    return USER in users


def check_repo_basedir(project, *perms):
    dirpath = os.path.join(DATADIR, project)

    if project.startswith("~"):
        allowed = (project == "~"+USER)
    else:
        allowed = any(check_acl(dirpath, p) for p in perms)

    return allowed, dirpath


def get_repo_basedir(project, error_msg, *perms):
    allowed, dirpath = check_repo_basedir(project, *perms)

    if not allowed:
        print >>sys.stderr, "ERROR: You are not allowed to", error_msg % project
        exit(1)

    return dirpath


def get_config_basedir(dirname):
    if dirname == '':
        dirpath = DATADIR
    else:
        dirpath = os.path.join(DATADIR, dirname)

    if not check_acl(dirpath, "config"):
        print >>sys.stderr, "ERROR: You are not allowed to configure %s" % dirname
        exit(1)

    return dirpath


def valid_name(string):
    if not NAME_RE.match(string):
        raise argparse.ArgumentTypeError("'%s'" % string)
    return string


def valid_project_name(string):
    if string.startswith('~'):
        return '~' + valid_name(string[1:])
    return valid_name(string)


def sanitize_path(path):
    dirname, basename = os.path.split(path)

    if dirname == '':
        dirname = '~'+USER
    elif dirname == '/':
        dirname = ''
    else:
        while dirname.startswith("/"):
            dirname = dirname[1:]

        if not NAME_RE.match(dirname[dirname.startswith("~"):]):
            print >>sys.stderr, "ERROR: Invalid path '%s'" % path
            exit(1)

    if not dirname.startswith("~"):
        if basename == CONFDIR:
            return dirname, basename

    if not NAME_RE.match(basename):
        print >>sys.stderr, "ERROR: Invalid path '%s'" % path
        exit(1)

    return dirname, basename


def is_public(path):
    return os.path.exists(os.path.join(path, GIT_DAEMON_EXPORT_OK))


def listdir(path, public_only=True):
    try:
        names = os.listdir(path)
    except OSError:
        return

    for name in names:
        dirpath = os.path.join(path, name)

        if not NAME_RE.match(name):
            continue

        if os.path.isdir(dirpath):
            if public_only and not is_public(dirpath):
                continue

            print name


command = Command(description='Gitto SSH Command')


@command(argument("project", type=valid_name, help="Project name"))
def create(project):
    """create new project"""

    if not check_acl(DATADIR, "create-project"):
        print >>sys.stderr, "ERROR: You are not allowed to create new project."
        exit(1)

    os.execlp(sys.executable, "python", "-m", "gitto", "init-project", project, USER)


@command()
def projects():
    """list projects"""

    for d in os.listdir(DATADIR):
        dirpath = os.path.join(DATADIR, d)

        if not NAME_RE.match(d):
            continue

        if os.path.isdir(dirpath):
            print d


@command(argument("--public", action='store_true', help="publish repository"),
         argument("project", nargs="?", type=valid_name, help="Project name"),
         argument("repo", type=valid_name, help="Repository name")) # XXX: public
def init(public, repo, project="~"+USER):
    """init repositories"""

    get_repo_basedir(project, "create new repository under '%s' project.", "create-repo")

    args = ["python", "-m", "gitto", "init-repo"]

    if public:
        args += ["--public"]

    args += [project, repo]

    os.execvp(sys.executable, args)


@command(argument("project", nargs="?", type=valid_project_name, help="Project name or '~'"))
def ls(project="~"+USER):
    """list repositories"""

    allowed, dirpath = check_repo_basedir(project, "list-repo")
    listdir(dirpath, public_only=not allowed)


@command(argument("project", nargs="?", type=valid_name, help="Project name"),
         argument("repo", type=valid_name, help="Repository name"))
def publish_repo(repo, project="~"+USER):
    """Publish repository"""

    dirpath = get_repo_basedir(project, "publish repository under '%s' project.", "publish-repo")

    export = os.path.join(dirpath, repo, GIT_DAEMON_EXPORT_OK)

    try:
        open(export, "w").close()
    except IOError:
        if not os.path.exists(export):
            print >>sys.stderr, "ERROR: Failed to publish repo '%s'." % repo
            exit(1)


@command(argument("project", nargs="?", type=valid_name, help="Project name"),
         argument("name", type=valid_name, help="Repository name"))
def unpublish_repo(repo, project="~"+USER):
    "Unpublish repository"

    dirpath = get_repo_basedir(project, "publish repository under '%s' project.", "publish-repo")

    export = os.path.join(dirpath, repo, GIT_DAEMON_EXPORT_OK)

    try:
        os.remove(export)
    except OSError:
        if os.path.exists(export):
            print >>sys.stderr, "ERROR: Failed to unpublish repo '%s'." % repo
            exit(1)


@command(argument("directory", help="Repository directory"))
def git_upload_pack(directory):
    """git-upload-pack"""

    dirname, basename = sanitize_path(directory)

    if basename == CONFDIR:
        dirpath = get_config_basedir(dirname)
    elif dirname != '':
        allowed, dirpath = check_repo_basedir(dirname, "pull:"+basename, "pull:*")

        if not allowed:
            if not is_public(os.path.join(dirpath, basename)):
                print >>sys.stderr, "ERROR: You are not allowed to pull from '%s/%s'" % (dirname, basename)
                exit(1)
    else:
        print >>sys.stderr, "ERROR: Invalid path '%s'" % directory
        exit(1)

    os.execlp("git-upload-pack", "git-upload-pack", os.path.join(dirpath, basename))


@command(argument("directory", help="Repository directory"))
def git_receive_pack(directory):
    """git-receive-pack"""

    dirname, basename = sanitize_path(directory)

    if basename == CONFDIR:
        dirpath = get_config_basedir(dirname)
    elif dirname != '':
        dirpath = get_repo_basedir(dirname, "push to '%%s/%s'" % basename, "push:"+basename, "push:*")
    else:
        print >>sys.stderr, "ERROR: Invalid path '%s'" % directory
        exit(1)

    os.execlp("git-receive-pack", "git-receive-pack", os.path.join(dirpath, basename))


@command()
def help():
    """Print help message"""

    command.print_help()


if __name__ == '__main__':
    command.run()
