"""Validate a pre-generated LiveTalking avatar before it is served."""

from __future__ import annotations

import argparse
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    message: str
    frame_count: int = 0


def _png_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.png"))


def _image_size(files: Iterable[Path], label: str) -> tuple[int, int] | str:
    expected: tuple[int, int] | None = None
    for image_path in files:
        try:
            with Image.open(image_path) as image:
                image.verify()
            with Image.open(image_path) as image:
                size = image.size
        except (OSError, UnidentifiedImageError) as exc:
            return f"{label}无法读取：{image_path.name}（{exc}）"
        if expected is None:
            expected = size
        elif size != expected:
            return f"{label}尺寸不一致：{image_path.name} 为 {size}，预期 {expected}"
    return expected or (0, 0)


def validate_avatar(path: Path, min_frames: int = 50) -> ValidationResult:
    avatar_path = Path(path)
    if not avatar_path.is_dir():
        return ValidationResult(False, f"Avatar 目录不存在：{avatar_path}")

    full_files = _png_files(avatar_path / "full_imgs")
    face_files = _png_files(avatar_path / "face_imgs")
    coords_path = avatar_path / "coords.pkl"
    if not coords_path.is_file():
        return ValidationResult(False, f"缺少坐标文件：{coords_path}")

    try:
        with coords_path.open("rb") as handle:
            coords = pickle.load(handle)
    except (OSError, EOFError, pickle.UnpicklingError) as exc:
        return ValidationResult(False, f"坐标文件无法读取：{exc}")

    counts = (len(full_files), len(face_files), len(coords))
    if len(set(counts)) != 1:
        return ValidationResult(
            False,
            "资源数量不一致："
            f"full_imgs={counts[0]}，face_imgs={counts[1]}，coords={counts[2]}",
        )
    if counts[0] < min_frames:
        return ValidationResult(
            False,
            f"Avatar 帧数不足：{counts[0]}，至少需要 {min_frames}",
            counts[0],
        )

    full_size = _image_size(full_files, "完整帧")
    if isinstance(full_size, str):
        return ValidationResult(False, full_size, counts[0])
    face_size = _image_size(face_files, "人脸帧")
    if isinstance(face_size, str):
        return ValidationResult(False, face_size, counts[0])

    return ValidationResult(
        True,
        f"Avatar 资源有效：{counts[0]} 帧，完整帧 {full_size[0]}×{full_size[1]}，"
        f"人脸帧 {face_size[0]}×{face_size[1]}",
        counts[0],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 LiveTalking Avatar 资源完整性")
    parser.add_argument("avatar_path", type=Path)
    parser.add_argument("--min-frames", type=int, default=50)
    args = parser.parse_args()

    result = validate_avatar(args.avatar_path, min_frames=args.min_frames)
    print(result.message)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
