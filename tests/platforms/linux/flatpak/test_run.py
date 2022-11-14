from unittest import mock

import pytest

from briefcase.console import Console, Log
from briefcase.exceptions import BriefcaseCommandError
from briefcase.integrations.flatpak import Flatpak
from briefcase.integrations.subprocess import Subprocess
from briefcase.platforms.linux.flatpak import LinuxFlatpakRunCommand


@pytest.fixture
def run_command(tmp_path):
    command = LinuxFlatpakRunCommand(
        logger=Log(),
        console=Console(),
        base_path=tmp_path / "base_path",
        data_path=tmp_path / "briefcase",
    )
    command.tools.flatpak = mock.MagicMock(spec_set=Flatpak)
    command.tools.subprocess = mock.MagicMock(spec_set=Subprocess)

    return command


def test_run(run_command, first_app_config):
    """A flatpak can be executed."""
    # Set up the log streamer to return a known stream
    log_popen = mock.MagicMock()
    run_command.tools.flatpak.run.return_value = log_popen

    # Run the app
    run_command.run_app(first_app_config)

    # App is executed
    run_command.tools.flatpak.run.assert_called_once_with(
        bundle="com.example",
        app_name="first-app",
    )

    # The streamer was started
    run_command.tools.subprocess.stream_output.assert_called_once_with(
        "first-app",
        log_popen,
    )

    # The stream was cleaned up
    run_command.tools.subprocess.cleanup.assert_called_once_with("first-app", log_popen)


def test_run_app_failed(run_command, first_app_config, tmp_path):
    """If there's a problem starting the app, an exception is raised."""
    run_command.tools.flatpak.run.side_effect = OSError

    with pytest.raises(BriefcaseCommandError):
        run_command.run_app(first_app_config)

    # The run command was still invoked
    run_command.tools.flatpak.run.assert_called_once_with(
        bundle="com.example",
        app_name="first-app",
    )

    # No attempt to stream was made
    run_command.tools.subprocess.stream_output.assert_not_called()


def test_run_ctrl_c(run_command, first_app_config, capsys):
    """When CTRL-C is sent while the App is running, Briefcase exits
    normally."""
    # Set up the log streamer to return a known stream
    log_popen = mock.MagicMock()
    run_command.tools.flatpak.run.return_value = log_popen

    # Mock the effect of CTRL-C being hit while streaming
    run_command.tools.subprocess.stream_output.side_effect = KeyboardInterrupt

    # Invoke run_app (and KeyboardInterrupt does not surface)
    run_command.run_app(first_app_config)

    # App is executed
    run_command.tools.flatpak.run.assert_called_once_with(
        bundle="com.example",
        app_name="first-app",
    )

    # An attempt was made to stream
    run_command.tools.subprocess.stream_output.assert_called_once_with(
        "first-app",
        log_popen,
    )

    # Shows the try block for KeyboardInterrupt was entered
    assert capsys.readouterr().out.endswith(
        "[first-app] Starting app...\n"
        "===========================================================================\n"
    )

    # The stream was cleaned up
    run_command.tools.subprocess.cleanup.assert_called_once_with("first-app", log_popen)
