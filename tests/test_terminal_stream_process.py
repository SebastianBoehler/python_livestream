import asyncio
import io
import subprocess
import threading
import unittest
from unittest.mock import AsyncMock, patch

from broadcast.terminal_stream_process import (
    next_reconnect_delay,
    run_ffmpeg_with_reconnect,
)
from broadcast.terminal_stream_config import TerminalStreamRuntimeError


class FakeExitedProcess:
    def __init__(self, return_code: int, stderr_line: str = "") -> None:
        self.return_code = return_code
        self.stderr = io.StringIO(stderr_line)

    def wait(self, timeout: float | None = None) -> int:
        return self.return_code

    def terminate(self) -> None:
        raise AssertionError("An exited process should not be terminated")

    def kill(self) -> None:
        raise AssertionError("An exited process should not be killed")


class FakeBlockingProcess:
    def __init__(self) -> None:
        self.stderr = io.StringIO("")
        self.wait_started = threading.Event()
        self.finished = threading.Event()
        self.terminated = False

    def wait(self, timeout: float | None = None) -> int:
        self.wait_started.set()
        if not self.finished.wait(timeout):
            raise subprocess.TimeoutExpired("ffmpeg", timeout)
        return -15

    def terminate(self) -> None:
        self.terminated = True
        self.finished.set()

    def kill(self) -> None:
        self.finished.set()


class ReconnectBackoffTests(unittest.TestCase):
    def test_backoff_is_short_bounded_and_resets_after_stable_session(self) -> None:
        failure_count = 0
        delays = []
        for _ in range(5):
            delay, failure_count = next_reconnect_delay(
                failure_count,
                session_duration_seconds=10,
            )
            delays.append(delay)

        self.assertEqual(delays, [1, 2, 5, 10, 10])
        self.assertEqual(
            next_reconnect_delay(
                failure_count,
                session_duration_seconds=300,
            ),
            (1, 1),
        )


class FfmpegReconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_start_failure_remains_fatal(self) -> None:
        with (
            patch(
                "broadcast.terminal_stream_process.subprocess.Popen",
                side_effect=OSError("spawn failed"),
            ),
            patch(
                "broadcast.terminal_stream_process.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep,
            self.assertRaisesRegex(
                TerminalStreamRuntimeError,
                "could not start",
            ),
        ):
            await run_ffmpeg_with_reconnect(
                ["ffmpeg", "-f", "flv", "/tmp/test.flv"],
                environment={"DISPLAY": ":99"},
                output_target="/tmp/test.flv",
            )

        sleep.assert_not_awaited()

    async def test_unexpected_exits_reconnect_without_exposing_output_target(
        self,
    ) -> None:
        output_target = "rtmps://a.rtmps.youtube.com/live2/secret-key-123456"
        processes = [
            FakeExitedProcess(1, f"Broken pipe writing {output_target}\n"),
            FakeExitedProcess(1),
        ]
        sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])

        with (
            patch(
                "broadcast.terminal_stream_process.subprocess.Popen",
                side_effect=processes,
            ) as popen,
            patch("broadcast.terminal_stream_process.asyncio.sleep", sleep),
            self.assertLogs(
                "broadcast.terminal_stream_process",
                level="INFO",
            ) as captured_logs,
            self.assertRaises(asyncio.CancelledError),
        ):
            await run_ffmpeg_with_reconnect(
                ["ffmpeg", "-f", "flv", output_target],
                environment={"DISPLAY": ":99"},
                output_target=output_target,
            )

        self.assertEqual(popen.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in popen.call_args_list],
            [
                ["ffmpeg", "-f", "flv", output_target],
                ["ffmpeg", "-f", "flv", output_target],
            ],
        )
        self.assertEqual(
            [call.args[0] for call in sleep.await_args_list],
            [1, 2],
        )
        combined_logs = "\n".join(captured_logs.output)
        self.assertNotIn("secret-key-123456", combined_logs)
        self.assertIn("rtmps://a.rtmps.youtube.com/<redacted>", combined_logs)

    async def test_cancellation_terminates_the_active_ffmpeg_process(self) -> None:
        process = FakeBlockingProcess()
        with patch(
            "broadcast.terminal_stream_process.subprocess.Popen",
            return_value=process,
        ):
            stream_task = asyncio.create_task(
                run_ffmpeg_with_reconnect(
                    ["ffmpeg", "-f", "flv", "/tmp/test.flv"],
                    environment={"DISPLAY": ":99"},
                    output_target="/tmp/test.flv",
                )
            )
            wait_started = await asyncio.to_thread(process.wait_started.wait, 1)
            self.assertTrue(wait_started)

            stream_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await stream_task

        self.assertTrue(process.terminated)


if __name__ == "__main__":
    unittest.main()
