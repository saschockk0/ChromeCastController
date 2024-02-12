##
##

import shutil
import subprocess
import ffmpeg
import os
import typer
from pathlib import Path
import signal


TV_MAGIC_DIR = Path("Z:/Магия/Покрутить видосики на экране")
TEMP = Path("C:/Users/Shuri/VideoTemp")
CONVERTED_VIDS = TEMP / "Converted"
FINAL_VIDEO = TEMP / "Final.mp4"
app = typer.Typer()

if not CONVERTED_VIDS.exists():
    CONVERTED_VIDS.mkdir(exist_ok=True, mode=777, parents=True)


def copy_files(source_folder: Path, dest_folder: Path, pattern: str = "*.mov") -> list[Path]:

    copied_files = []
    temp_files_stemd = []

    for temp_file in dest_folder.glob(pattern):  # Сбор абсолютных путей файлов в массив
        temp_files_stemd.append(f"{temp_file.stem}{temp_file.suffix}")

    for ffmpeg_video in source_folder.glob(pattern):
        if ffmpeg_video.name not in temp_files_stemd:
            dest = Path(f"{dest_folder}/{ffmpeg_video.name}")
            shutil.copyfile(ffmpeg_video, dest)
            copied_files.append(dest)

    return copied_files


def diff_and_remove_files(magic_folder: Path, temp_folder: Path, pattern: str = "*"):
    deleted_files = []
    magic_folder_file_names = [i.stem for i in magic_folder.glob(pattern)]
    for temp_file in temp_folder.glob(pattern):
        if temp_file.stem in magic_folder_file_names or temp_file.name == "Converted":
            continue
        deleted_files.append(temp_file)
        os.remove(temp_file)
    return deleted_files


videos_to_convert = list(Path(TEMP).glob("*.mov"))

converted = list(Path(CONVERTED_VIDS).glob("*.mp4"))
converted_names = [i.stem for i in converted]


def convert_rotate(paths_to_convert: list[Path], suffix ,output_folder: Path) -> list[Path]:
    converted_files = []
    for video in paths_to_convert:
        if f"{video.stem}" in converted_names:
            print(f"skipping {video.stem}")
            continue
        output_file = Path(f"{output_folder}/{video.stem}.{suffix}")  # todo move suffix(converted.mp4) to arg
        converted_files.append(output_file)

        ffmpeg_video = ffmpeg.input(video)
        ffmpeg_video = ffmpeg.filter(ffmpeg_video,'transpose', 1)
        ffmpeg_video = ffmpeg.output(ffmpeg_video, filename=output_file)

        ffmpeg.run(ffmpeg_video)

    return converted_files


def concatenate(videos_to_concatenate: list[Path], output_file: Path):
    main_video = ffmpeg.input(converted.pop(0))

    for video in videos_to_concatenate:
        video_to_concat = ffmpeg.input(video)
        main_video = ffmpeg.concat(main_video, video_to_concat)

    main_video = ffmpeg.output(main_video, filename=output_file)
    ffmpeg.run(main_video)


def get_paths(path: Path, pattern: str) -> list[Path]:
    return list(path.glob(pattern))


def start_vlc():
    debug = subprocess.Popen(
        [
            "C:/Program Files/VideoLAN/VLC/vlc.exe",
            FINAL_VIDEO,
            "--sout=#chromecast",
            "--sout-chromecast-ip=10.2.0.25",
            "--demux-filter=demux_chromecast",
            "-R"
        ]
    )
    pass


def kill_vlc():
    return os.system("taskkill /im vlc.exe")


def main():
    copied_files = copy_files(TV_MAGIC_DIR, TEMP, "*.mov")
    diff_and_remove_files(TV_MAGIC_DIR, TEMP)
    deleted_files = diff_and_remove_files(TV_MAGIC_DIR, CONVERTED_VIDS)
    convert_rotate(list(Path(TEMP).glob("*.mov")),"mp4",CONVERTED_VIDS)
    # todo do not convert already converted vids (line60?)
    if len(copied_files) > 0 or len(deleted_files) > 0 or not FINAL_VIDEO.exists():
        kill_vlc()
        concatenate(get_paths(CONVERTED_VIDS, pattern="*.mp4"), FINAL_VIDEO)
        start_vlc()

if __name__ == "__main__":
    typer.run(main)

