import pickle
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def build_avatar_fixture(
    root: Path,
    *,
    full: int,
    face: int,
    coords: int,
    image_size: tuple[int, int] = (32, 24),
) -> Path:
    avatar = root / "avatar"
    full_dir = avatar / "full_imgs"
    face_dir = avatar / "face_imgs"
    full_dir.mkdir(parents=True)
    face_dir.mkdir(parents=True)

    width, height = image_size
    full_image = Image.new("RGB", (width, height), color=(127, 127, 127))
    face_image = Image.new("RGB", (16, 16), color=(127, 127, 127))
    for index in range(full):
        full_image.save(full_dir / f"{index:08d}.png")
    for index in range(face):
        face_image.save(face_dir / f"{index:08d}.png")

    with (avatar / "coords.pkl").open("wb") as handle:
        pickle.dump([(0, 16, 0, 16)] * coords, handle)
    return avatar


def test_rejects_mismatched_frame_and_coordinate_counts(tmp_path):
    from tools.validate_avatar_asset import validate_avatar

    avatar = build_avatar_fixture(tmp_path, full=3, face=3, coords=2)
    result = validate_avatar(avatar, min_frames=1)
    assert not result.ok
    assert "数量不一致" in result.message


def test_accepts_complete_dynamic_avatar(tmp_path):
    from tools.validate_avatar_asset import validate_avatar

    avatar = build_avatar_fixture(tmp_path, full=3, face=3, coords=3)
    result = validate_avatar(avatar, min_frames=1)
    assert result.ok


def test_rejects_inconsistent_full_frame_dimensions(tmp_path):
    from tools.validate_avatar_asset import validate_avatar

    avatar = build_avatar_fixture(tmp_path, full=3, face=3, coords=3)
    different = Image.new("RGB", (20, 20), color=(127, 127, 127))
    different.save(avatar / "full_imgs" / "00000002.png")

    result = validate_avatar(avatar, min_frames=1)

    assert not result.ok
    assert "尺寸不一致" in result.message


def test_start_script_validates_selected_avatar_before_starting(tmp_path):
    git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if not git_bash.exists():
        raise AssertionError("测试需要 Git Bash")

    project = tmp_path / "LiveTalking"
    (project / "models").mkdir(parents=True)
    (project / "models" / "wav2lip.pth").touch()
    (project / "data" / "avatars" / "doctor_natural").mkdir(parents=True)
    (project / "data" / "avatars" / "doctor_natural" / "coords.pkl").touch()
    (project / "tools").mkdir()
    shutil.copy(Path(__file__).parents[1] / "start.sh", project / "start.sh")
    (project / "tools" / "validate_avatar_asset.py").write_text(
        "import sys\nprint('VALIDATED=' + sys.argv[1])\nraise SystemExit(23)\n",
        encoding="utf-8",
    )

    environment = os.environ.copy()
    environment["AVATAR_ID"] = "doctor_natural"
    completed = subprocess.run(
        [str(git_bash), project.joinpath("start.sh").as_posix()],
        cwd=project,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 23
    assert "data/avatars/doctor_natural" in completed.stdout.replace("\\", "/")
