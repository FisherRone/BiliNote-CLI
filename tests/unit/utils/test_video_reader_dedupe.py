import pathlib
import re
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from app.utils.video_reader import VideoReader


def _make_fake_ffmpeg_runner(colors_by_second):
    def _runner(cmd, check=True):
        output_path = next((arg for arg in cmd if isinstance(arg, str) and arg.endswith(".jpg")), None)
        if output_path is None:
            raise AssertionError("Output path not found in ffmpeg cmd")
        match = re.search(r"frame_(\d{2})_(\d{2})\.jpg$", output_path)
        if match is None:
            raise AssertionError("Unexpected output path")
        sec = int(match.group(1)) * 60 + int(match.group(2))
        payload = colors_by_second[sec]
        with open(output_path, "wb") as f:
            f.write(payload)
        return 0

    return _runner


class TestVideoReaderDeduplicateFrames(unittest.TestCase):
    def test_extract_frames_skips_adjacent_duplicates_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            frame_dir = pathlib.Path(tmp_dir) / "frames"
            grid_dir = pathlib.Path(tmp_dir) / "grids"
            reader = VideoReader(
                video_path="dummy.mp4",
                frame_interval=1,
                frame_dir=str(frame_dir),
                grid_dir=str(grid_dir),
            )

            fake_colors = {
                0: b"frame-a",
                1: b"frame-a",
                2: b"frame-b",
                3: b"frame-b",
            }

            with patch("app.utils.video_reader.ffmpeg.probe", return_value={"format": {"duration": "4"}}), \
                    patch("app.utils.video_reader.subprocess.run", side_effect=_make_fake_ffmpeg_runner(fake_colors)):
                paths = reader.extract_frames(max_frames=10)

            names = [pathlib.Path(p).name for p in paths]
            self.assertEqual(names, ["frame_00_00.jpg", "frame_00_02.jpg"])


if __name__ == "__main__":
    unittest.main()
