import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main  # noqa: E402
from utils.enums import Mode  # noqa: E402


class FakeShutdownEvent:
    def __init__(self):
        self.was_set = False

    def set(self):
        self.was_set = True


class FakeProcess:
    instances = []

    def __init__(self, target, args):
        self.args = args
        self.join_timeouts = []
        self.terminated = False
        FakeProcess.instances.append(self)

    def start(self):
        pass

    def join(self, timeout=None):
        self.join_timeouts.append(timeout)
        if timeout is None:
            raise KeyboardInterrupt

    def is_alive(self):
        return not self.terminated

    def terminate(self):
        self.terminated = True


def test_multi_user_interrupt_requests_shutdown_before_termination(monkeypatch):
    shutdown_event = FakeShutdownEvent()
    FakeProcess.instances = []
    args = SimpleNamespace(
        user=["creator-one", "creator-two"],
        url=None,
        room_id=None,
        automatic_interval=5,
        proxy=None,
        output=None,
        duration=None,
        exit_on_interrupt=False,
        telegram=False,
        bitrate=None,
        ffmpeg_path=None,
    )

    monkeypatch.setattr(main.multiprocessing, "Event", lambda: shutdown_event)
    monkeypatch.setattr(main.multiprocessing, "Process", FakeProcess)
    monkeypatch.setattr(main.time, "monotonic", lambda: 0)

    main.run_recordings(args, Mode.AUTOMATIC, cookies={})

    assert shutdown_event.was_set is True
    assert [process.args[0].shutdown_event for process in FakeProcess.instances] == [
        shutdown_event,
        shutdown_event,
    ]
    assert all(process.terminated for process in FakeProcess.instances)
    assert all(
        main.SHUTDOWN_GRACE_SECONDS in process.join_timeouts
        for process in FakeProcess.instances
    )
