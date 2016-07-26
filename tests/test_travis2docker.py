
import os
import sys

from travis2docker.cli import main


def test_main():
    # TODO: fix duplicated code
    # TODO: Delete the files created by each test
    dirname_example = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'examples')
    argv = ["travis2docker", 'foo', 'bar', "--no-clone"]

    example = os.path.join(dirname_example, 'example_1.yml')
    sys.argv = argv + ['--travis-yml-path', example]
    scripts = main()
    assert len(scripts) == 1, "Scripts returned should be 1 for %s" % example

    example = os.path.join(dirname_example, 'example_2.yml')
    sys.argv = argv + ['--travis-yml-path', example]
    scripts = main()
    assert len(scripts) == 1, "Scripts returned should be 1 for %s" % example
    with open(os.path.join(scripts[0], "Dockerfile")) as f_dkr:
        dkr_content = f_dkr.read()
        assert 'ENV VARIABLE="value"' in dkr_content

    example = os.path.join(dirname_example, 'example_3.yml')
    sys.argv = argv + ['--travis-yml-path', example]
    scripts = main()
    assert len(scripts) == 2, "Scripts returned should be 2 for %s" % example
    with open(os.path.join(scripts[0], "Dockerfile")) as f_dkr:
        dkr_content = f_dkr.read()
        assert 'VARIABLE_GLOBAL="value global"' in dkr_content
        assert 'VARIABLE_MATRIX_1="value matrix 1"' in dkr_content
    with open(os.path.join(scripts[1], "Dockerfile")) as f_dkr:
        dkr_content = f_dkr.read()
        assert 'VARIABLE_GLOBAL="value global"' in dkr_content
        assert 'VARIABLE_MATRIX_2="value matrix 2"' in dkr_content
