import os
import os.path
import sys
import ConfigParser
import subprocess
import shutil
import stat

from .command import Command, argument


DATADIR = os.environ.get("GITTO_DATADIR", "data")
GIT_DAEMON_EXPORT_OK = "git-daemon-export-ok"
BANNER = '\n'.join([
r"""             _ __  __       """,
r"""      ____ _(_) /_/ /_____  """,
r"""     / __ `/ / __/ __/ __ \ """,
r"""    / /_/ / / /_/ /_/ /_/ / """,
r"""    \__, /_/\__/\__/\____/  """,
r"""   /____/                   """,
r"""""",
r"""You've successfully authenticated,""",
r"""but we provide no shell access""",
r""""""])


def config(*configs):
    conf = ConfigParser.SafeConfigParser(allow_no_value=True)

    for c in configs:
        if not conf.has_section(c[0]):
            conf.add_section(c[0])

        conf.set(*c)

    return conf


def write_config(path, *configs):
    conf = config(*configs)

    with open(path, "w") as f:
        conf.write(f)


def git(gitdir, *commands):
    p = subprocess.Popen(("git",)+commands, close_fds=True, cwd=gitdir)
    p.communicate()
    return p


def git_init(path, bare, *extra):
    if not bare:
        repopath = os.path.join(path, '.git')
    else:
        repopath = path

    write_config(
        os.path.join(repopath, "config"),
        ('core', 'repositoryformatversion', '0'),
        ('core', 'filemode', 'true'),
        ('core', 'bare', 'true' if bare else 'false'),
        *extra)

    with open(os.path.join(repopath, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    os.mkdir(os.path.join(repopath, "objects"))
    os.mkdir(os.path.join(repopath, "objects", "pack"))
    os.mkdir(os.path.join(repopath, "objects", "info"))
    os.mkdir(os.path.join(repopath, "refs"))
    os.mkdir(os.path.join(repopath, "refs", "heads"))
    os.mkdir(os.path.join(repopath, "refs", "tags"))


def config_repo_init(confdir, creator):
    git_init(confdir, False,
             ('user', 'name', creator),
             ('user', 'email', creator+"@gitto"),
             ('receive', 'denyCurrentBranch', 'ignore'))

    git(confdir, "add", ".")
    git(confdir, "commit", "-a", "-m", "Initial commit")


command = Command(description='Gitto Initialize Command')


@command(argument("username", help="name of superuser"),
         argument("pkey", help="path to superuser's pubkey"),
         argument("datadir", nargs='?', help="path to data directory, defaults to data"))
def init(username, pkey, datadir=DATADIR):
    """Initialize Gitto data directory"""

    try:
        os.mkdir(datadir)
    except OSError:
        assert os.path.exists(datadir), "Failed to create datadir"

    confdir = os.path.join(datadir, ".config")
    os.mkdir(confdir)
    os.mkdir(os.path.join(confdir, "keys"))
    os.mkdir(os.path.join(confdir, ".git"))

    shutil.copy(pkey, os.path.join(confdir, "keys", username))

    with open(os.path.join(confdir, "BANNER"), "w") as f:
        f.write(BANNER)

    write_config(
        os.path.join(confdir, "acl.conf"),
        ('config', username),
        ('create-project', username))

    os.mkdir(os.path.join(confdir, "hooks"))
    repo_post_receive = os.path.join(confdir, "hooks", "post-receive")
    with open(repo_post_receive, "w") as f:
        f.write("#!/bin/sh\nrepo_hook=\"hooks/post-receive`echo ${PWD} | awk -F/ '{print $(NF -1)\\\"-\\\"$NF}' | sed 's/^~/_/;tx;s/^/-/;:x'`\"\n\nif [ -x ${repo_hook} ]; then\n  exec ${repo_hook}\nfi\n")

    os.chmod(repo_post_receive, os.stat(repo_post_receive)[0] | stat.S_IXUSR)

    os.mkdir(os.path.join(confdir, "config-hooks"))
    post_receive = os.path.join(confdir, "config-hooks", "post-receive")
    with open(post_receive, "w") as f:
        f.write("#!/bin/sh\ncd ..\nenv -i - git reset --hard HEAD\n")

    os.chmod(post_receive, os.stat(post_receive)[0] | stat.S_IXUSR)

    config_repo_init(confdir, username)
    hooksdir = os.path.join("..", "config-hooks")
    os.symlink(hooksdir, os.path.join(confdir, ".git", "hooks"))


@command(argument("project", help="project name"),
         argument("creator", help="name of creator"),
         argument("datadir", nargs='?', help="path to data directory, defaults to data"))
def init_project(project, creator, datadir=DATADIR):
    """Initialize project"""

    dirpath = os.path.join(datadir, project)

    try:
        os.mkdir(dirpath)
    except OSError:
        print >>sys.stderr, "Failed to create project '%s'" % project
        exit(1)

    confdir = os.path.join(dirpath, ".config")
    os.mkdir(confdir)
    os.mkdir(os.path.join(confdir, ".git"))

    write_config(
        os.path.join(confdir, "acl.conf"),
        ('config', creator),
        ('create-repo', creator),
        ('list-repo', creator),
        ('push:*', creator),
        ('pull:*', creator))

    config_repo_init(confdir, creator)
    hooksdir = os.path.join("..", "..", "..", ".config", "config-hooks")
    os.symlink(hooksdir, os.path.join(confdir, ".git", "hooks"))


@command(argument("--public", action="store_true", help="publish repository"),
         argument("project", help="project name"),
         argument("repo", help="repository name"),
         argument("datadir", nargs='?', help="path to data directory, defaults to data"))
def init_repo(project, repo, public, datadir=DATADIR):
    """Initialize repository"""

    dirpath = os.path.join(datadir, project)

    if project.startswith("~"):
        try:
            os.mkdir(dirpath)
        except OSError:
            if not os.path.exists(dirpath):
                print >>sys.stderr, "Failed to initialize directory '%s'" % project
                exit(1)

    repopath = os.path.join(dirpath, repo)

    try:
        os.mkdir(repopath)
    except OSError:
        print >>sys.stderr, "Failed to create repository '%s'" % repo
        exit(1)

    git_init(repopath, True)
    hooksdir = os.path.join("..", "..", ".config", "hooks")
    os.symlink(hooksdir, os.path.join(repopath, "hooks"))

    if public:
        open(os.path.join(repopath, GIT_DAEMON_EXPORT_OK), "w").close()



if __name__ == '__main__':
    command.run()
