##
##
import shutil
import subprocess
import ffmpeg
import os
import typer
import psutil
from pathlib import Path
import sys


app = typer.Typer()
EXCEPTIONS = [".DS_STORE", "Инструкция", "Converted", "Final"]


def copy_files(source_folder: Path, dest_folder: Path, pattern: str = "*.mov") -> list[Path]:

    copied_files = []
    dest_dir_files_stemd = []

    for dest_dir_file in dest_folder.glob(pattern):  # Сбор абсолютных путей файлов в массив
        dest_dir_files_stemd.append(f"{dest_dir_file.stem}{dest_dir_file.suffix}")

    for ffmpeg_video in source_folder.glob(pattern): # Проверка наличия файлов в папке назначения
        if ffmpeg_video.name not in dest_dir_files_stemd:
            dest = Path(f"{dest_folder}/{ffmpeg_video.name}")
            shutil.copyfile(ffmpeg_video, dest)
            print(f"Copying {ffmpeg_video.name} into {dest_folder}")
            copied_files.append(dest)

    return copied_files


def diff_files(source_folder: Path, dest_dir: Path, source_pattern: str = "*", dest_pattern: str = "*") -> list[Path]:
    # returns files that presented in dest_dir yet not in source_folder
    files = []
    source_folder_names = [i.stem for i in source_folder.glob(source_pattern)]
    dest_dir_files = list(dest_dir.glob(dest_pattern))
    for dest_dir_file in dest_dir_files:
        if dest_dir_file.stem not in source_folder_names and dest_dir_file.stem not in EXCEPTIONS:
            files.append(dest_dir_file)
    return files


# Сравнение и удаление файлов в папках
def diff_and_remove_files(source_folder: Path, dest_dir: Path, source_pattern: str = "*", dest_pattern: str = "*"):
    to_remove = diff_files(source_folder, dest_dir, source_pattern=source_pattern, dest_pattern=dest_pattern)
    if len(to_remove) > 0:
        kill_vlc()

    for dest_dir_file in to_remove:
        print(f"Removing file {dest_dir_file}")
        os.remove(dest_dir_file)
    return to_remove


# videos_to_convert = list(Path(dest_dir).glob("*.mov"))


# Конвертация видео из папки VideoTemp
def convert_rotate(paths_to_convert: list[Path], output_folder: Path, suffix: str) -> list[Path]:
    converted_files = []
    for video in paths_to_convert:
        output_file = Path(f"{output_folder}/{video.stem}.{suffix}")
        converted_files.append(output_file)

        print(f"Converting video {video}")
        ffmpeg_video = ffmpeg.input(video)
        ffmpeg_video = ffmpeg.filter(ffmpeg_video, 'transpose', 1)
        ffmpeg_video = ffmpeg.output(ffmpeg_video, filename=output_file)

        ffmpeg.run(ffmpeg_video)
        print(f"Successfully converted to {ffmpeg_video}")

    return converted_files


# Конкатенация сконвертированных видео
def concatenate(videos_to_concatenate: list[Path], output_file: Path):
    # if len(videos_to_concatenate) > 0:
    main_video = ffmpeg.input(videos_to_concatenate.pop(0))

    for video in videos_to_concatenate:
        video_to_concat = ffmpeg.input(video)
        main_video = ffmpeg.concat(main_video, video_to_concat)

    main_video = ffmpeg.output(main_video, filename=output_file)
    print("Concatenating main video")
    ffmpeg.run(main_video, overwrite_output=True)


def get_files(path: Path, pattern: str) -> list[Path]:
    return list(path.glob(pattern))


#Жив ли влц?
def vlc_alive() -> bool:
    for process in psutil.process_iter():
        if process.name() == "vlc.exe":
            return True
    return False



def start_vlc(video: Path):
    print("Starting VLC")
    subprocess.Popen(
        [
            "C:/Program Files/VideoLAN/VLC/vlc.exe",
            video,
            "--sout=#chromecast",
            "--sout-chromecast-ip=10.2.0.25",
            "--demux-filter=demux_chromecast",
            "-R"
        ]
    )

@app.command()
def kill_vlc():
    try:
        print("Killing VLC process")
        os.system("taskkill /f /im vlc.exe")
    except: #Код ошибки?
        return print("Error occurred during killing VLC process")
    else:
        return  print("Successfully killed VLC process")


@app.command()
def main(source_dir: Path, dest_dir:  Path):
    # source_dir = Path("Z:/Магия/Покрутить видосики на экране")
    # dest_dir = Path("C:/Users/Shuri/Videotmep")

    converted_videos_folder = dest_dir / "Converted"
    final_folder = converted_videos_folder / "Final"
    final_video = final_folder / "Final.mp4"

    if not final_folder.exists():
        final_folder.mkdir(exist_ok=True, mode=777, parents=True)

    diff_and_remove_files(source_dir, dest_dir, source_pattern="*.mov", dest_pattern="*.mov")
    deleted_files = diff_and_remove_files(source_dir, converted_videos_folder, source_pattern="*.mov", dest_pattern="*.mp4")
    copied_files = copy_files(source_dir, dest_dir, "*.mov")

    convert_rotate(copied_files, converted_videos_folder, suffix="mp4")

    if len(copied_files) > 0 or len(deleted_files) > 0 or not final_video.exists():
        kill_vlc()
        concatenate(get_files(converted_videos_folder, pattern="*.mp4"), final_video)
        start_vlc(final_video)
    else:
        if vlc_alive() is False:
            start_vlc(final_video)


if __name__ == "__main__":
    typer.run(main)
    # diff_files(Path("Z:/Магия/Покрутить видосики на экране"), Path("C:/Users/Shuri/VideoTemp"))
