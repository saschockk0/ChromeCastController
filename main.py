import shutil
import subprocess
import ffmpeg
import os
import typer
import psutil
import time
import logging
from pathlib import Path

app = typer.Typer()
EXCEPTIONS = [".DS_STORE", "Инструкция", "Converted", "Final"]
logging.basicConfig(level=logging.INFO, filename="tv_log.log", format="%(asctime)s %(levelname)s %(message)s")
os.chmod("./tv_log.log", 0o777)
logger = logging.getLogger(__name__)


def copy_files(source_folder: Path, dest_folder: Path, pattern: str = "*.mov") -> list[Path]:
    copied_files = []
    dest_dir_files_stemd = [f"{f.stem}{f.suffix}" for f in dest_folder.glob(pattern)]

    for ffmpeg_video in source_folder.glob(pattern):
        if ffmpeg_video.name not in dest_dir_files_stemd:
            dest = dest_folder / ffmpeg_video.name
            shutil.copyfile(ffmpeg_video, dest)
            logger.info(f"Copying {ffmpeg_video.name} into {dest_folder}")
            copied_files.append(dest)

    return copied_files


def diff_files(source_folder: Path, dest_dir: Path, source_pattern: str = "*", dest_pattern: str = "*") -> list[Path]:
    source_folder_names = {i.stem for i in source_folder.glob(source_pattern)}
    dest_dir_files = list(dest_dir.glob(dest_pattern))
    files = [f for f in dest_dir_files if f.stem not in source_folder_names and f.stem not in EXCEPTIONS]
    return files


def diff_and_remove_files(source_folder: Path, dest_dir: Path, source_pattern: str = "*", dest_pattern: str = "*"):
    to_remove = diff_files(source_folder, dest_dir, source_pattern=source_pattern, dest_pattern=dest_pattern)

    for dest_dir_file in to_remove:
        logger.info(f"Removing file {dest_dir_file}")
        os.remove(dest_dir_file)

    return to_remove


def convert_rotate(paths_to_convert: list[Path], output_folder: Path, suffix: str) -> list[Path]:
    converted_files = []

    for video in paths_to_convert:
        output_file = output_folder / f"{video.stem}.{suffix}"
        converted_files.append(output_file)

        logger.info(f"Converting video {video}")
        ffmpeg_video = ffmpeg.input(video)
        ffmpeg_video = ffmpeg.filter(ffmpeg_video, 'transpose', 1)
        ffmpeg_video = ffmpeg.output(ffmpeg_video, filename=output_file)

        ffmpeg.run(ffmpeg_video)
        logger.info(f"Successfully converted to {output_file}")

    return converted_files


def concatenate(videos_to_concatenate: list[Path], output_file: Path):
    try:
        main_video = ffmpeg.input(videos_to_concatenate.pop(0))
    except IndexError:
        logger.error("List is empty, cannot pop main video")

    for video in videos_to_concatenate:
        video_to_concat = ffmpeg.input(video)
        main_video = ffmpeg.concat(main_video, video_to_concat)

    main_video = ffmpeg.output(main_video, filename=output_file)
    logger.info("Concatenating main video")
    ffmpeg.run(main_video, overwrite_output=True)


def get_files(path: Path, pattern: str) -> list[Path]:
    return list(path.glob(pattern))


def vlc_alive() -> bool:
    logger.info("Checking VLC process")
    return any(process.name() == "vlc.exe" for process in psutil.process_iter())


def start_vlc(video: Path):
    logging.info("Starting VLC")
    subprocess.Popen([
        "C:/Program Files/VideoLAN/VLC/vlc.exe",
        video,
        "--sout=#chromecast",
        "--sout-chromecast-ip=10.2.0.25",
        "--demux-filter=demux_chromecast",
        "-R"
    ])


@app.command()
def kill_vlc():
    try:
        logger.info("Killing VLC process")
        os.system("taskkill /f /im vlc.exe")
    except Exception as e:
        logger.info(f"Error occurred during killing VLC process: {e}")
    else:
        logger.info("Successfully killed VLC process")


def swap_video(copied_files: list[Path], deleted_files: list[Path], converted_videos_folder: Path, final_video: Path,
               temp_final_video: Path):
    if copied_files or deleted_files or not final_video.exists():
        concatenate(get_files(converted_videos_folder, pattern="*.mp4"), temp_final_video)
        kill_vlc()

        if final_video.exists():
            time.sleep(5)
            os.remove(final_video)
        os.rename(temp_final_video, final_video)
        start_vlc(final_video)
    elif not vlc_alive():
        start_vlc(final_video)


@app.command()
def main(source_dir: Path, dest_dir: Path):
    converted_videos_folder = dest_dir / "Converted"
    final_folder = converted_videos_folder / "Final"
    final_video = final_folder / "Final.mp4"
    temp_final_video = final_folder / "TempFinal.mp4"

    if not final_folder.exists():
        logger.info("Creating final folder")
        final_folder.mkdir(exist_ok=True, mode=777, parents=True)

    diff_and_remove_files(source_dir, dest_dir, source_pattern="*.mov", dest_pattern="*.mov")
    deleted_files = diff_and_remove_files(
        source_dir,
        converted_videos_folder,
        source_pattern="*.mov",
        dest_pattern="*.mp4"
    )
    copied_files = copy_files(source_dir, dest_dir, "*.mov")

    convert_rotate(copied_files, converted_videos_folder, suffix="mp4")
    swap_video(copied_files, deleted_files, converted_videos_folder, final_video, temp_final_video)


if __name__ == "__main__":
    typer.run(main)
