import asyncio
import sys
from pathlib import Path

from cli_editor.services.runner import Runner, build_command


def test_build_command_for_python(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    command = build_command(path)
    assert command.error == ""
    assert command.argv is not None
    assert command.argv[0] == sys.executable
    assert command.argv[1] == "-u"
    assert command.argv[2] == str(path)


def test_build_command_for_javascript(tmp_path: Path) -> None:
    path = tmp_path / "a.js"
    command = build_command(path, node_path="/usr/bin/node")
    assert command.argv == ["/usr/bin/node", str(path)]
    missing = build_command(path, node_path="")
    assert "node is not installed" in missing.error


def test_build_command_for_html_and_css(tmp_path: Path) -> None:
    html = build_command(tmp_path / "index.html")
    assert html.open_path == tmp_path / "index.html"
    css = build_command(tmp_path / "style.css")
    assert "can't be run" in css.error
    unknown = build_command(tmp_path / "notes.txt")
    assert "Don't know how to run" in unknown.error


async def test_runner_streams_output_and_exit_code(tmp_path: Path) -> None:
    script = tmp_path / "hello.py"
    script.write_text("print('RUNOK')\n", encoding="utf-8")
    lines: list[str] = []
    codes: list[int] = []
    done = asyncio.Event()

    def on_done(code: int) -> None:
        codes.append(code)
        done.set()

    runner = Runner(lines.append, on_done)
    await runner.start(script)
    await asyncio.wait_for(done.wait(), timeout=5)
    assert "RUNOK" in lines
    assert codes == [0]
    assert runner.running is False


async def test_runner_stop_terminates_process(tmp_path: Path) -> None:
    script = tmp_path / "slow.py"
    script.write_text(
        "import time\nprint('STARTED', flush=True)\ntime.sleep(30)\n",
        encoding="utf-8",
    )
    lines: list[str] = []
    codes: list[int] = []
    done = asyncio.Event()

    def on_done(code: int) -> None:
        codes.append(code)
        done.set()

    runner = Runner(lines.append, on_done)
    await runner.start(script)
    for _ in range(100):
        if "STARTED" in lines:
            break
        await asyncio.sleep(0.05)
    assert "STARTED" in lines
    await runner.stop()
    await asyncio.wait_for(done.wait(), timeout=5)
    assert runner.stopped is True
    assert runner.running is False
    assert codes
