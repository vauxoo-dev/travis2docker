"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mtravis2docker` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``travis2docker.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``travis2docker.__main__`` in ``sys.modules``.

"""
import argparse

from . travis2docker import Travis2Docker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "git_repo_url",
        help="Specify repository git of work."
             "\nThis is used to clone it "
             "and get file .travis.yml or .shippable.yml"
             "\nIf your repository is private, "
             "don't use https url, "
             "use ssh url",
    )
    parser.add_argument(
        "git_revision",
        help="Revision git of work."
             "\nYou can use "
             "branch name e.g. master or 8.0 "
             "or pull number with 'pull/#' e.g. pull/1 "
             "NOTE: A sha e.g. b48228 NOT IMPLEMENTED YET",
    )
    parser.add_argument(
        '--docker-user', dest='docker_user',
        help="User of work into Dockerfile."
             "\nBased on your docker image."
             "\nDefault: root",
        default='root'
    )
    parser.add_argument(
        '--docker-image', dest='default_docker_image',
        help="Docker image to use by default in Dockerfile."
             "\nUse this parameter if don't "
             "exists value: 'build_image: IMAGE_NAME' "
             "in .travis.yml"
             "\nDefault: 'vauxoo/odoo-80-image-shippable-auto'",
        default='vauxoo/odoo-80-image-shippable-auto'
    )
    parser.add_argument(
        '--root-path', dest='root_path',
        help="Root path to save scripts generated."
             "\nDefault: 'tmp' dir of your O.S.",
        default=None,
    )
    parser.add_argument(
        '--add-remote', dest='remotes',
        help='Add git remote to git of build path, separated by a comma.'
             "\nUse remote name. E.g. 'Vauxoo,moylop260'",
    )
    parser.add_argument(
        '--exclude-after-success', dest='exclude_after_success',
        action='store_true', default=False,
        help='Exclude `travis_after_success` section to entrypoint',
    )
    parser.add_argument(
        '--run-extra-args', dest='run_extra_args',
        help="Extra arguments to `docker run RUN_EXTRA_ARGS` command",
        default='-itP -e LANG=C.UTF-8',
    )
    parser.add_argument(
        '--include-cleanup', dest='include_cleanup',
        action='store_true', default=False,
        help='Remove the docker container/image when done testing',
    )
    parser.add_argument(
        '--build-extra-args', dest='build_extra_args',
        help="Extra arguments to `docker build BUILD_EXTRA_ARGS` command",
        default='--rm',
    )
    parser.add_argument(
        '--travis-yml-path', dest='travis_yml_path',
        help="Path of file .travis.yml to use.",
        default=None,
    )

    args = parser.parse_args()
    sha = args.git_revision
    git_repo = args.git_repo_url
    docker_user = args.docker_user
    root_path = args.root_path
    default_docker_image = args.default_docker_image
    remotes = args.remotes and args.remotes.split(',')
    exclude_after_success = args.exclude_after_success
    run_extra_args = args.run_extra_args
    build_extra_args = args.build_extra_args
    include_cleanup = args.include_cleanup
    travis_yml_path = args.travis_yml_path
    t2d = Travis2Docker(
        yml_path=travis_yml_path,
        work_path=root_path,
        image=default_docker_image,
        os_kwargs={
            'user': docker_user,
            'repo_owner': 'Vauxoo',
            'repo_project': 'yoytec',
            'add_self_rsa_pub': True,
            'remotes': remotes,
            'revision': 'pull/2',
            'git_email': 'moylop@vx.com',
            'git_user': 'moy6',
        },
        copy_paths=[("$HOME/.ssh", "$HOME/.ssh")]
    )
    t2d.run_extra_params = run_extra_args
    t2d.build_extra_params = build_extra_args
    return t2d.compute_dockerfile(skip_after_success=exclude_after_success)
