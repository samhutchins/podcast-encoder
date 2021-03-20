#!/usr/bin/env python3

import struct
import collections
import os
from os.path import basename
from .wave_file import WaveFile
from argparse import ArgumentParser, Namespace
from subprocess import Popen, PIPE, run, DEVNULL
from threading import Thread
from io import BytesIO
from mutagen import id3
from typing import Tuple, List, IO, Dict, Any
from sys import exit

from .__init__ import __version__

version = f"""\
encode-podcast {__version__}
Copyright (c) 2018,2021 Sam Hutchins\
"""

help = f"""\
Transcode WAV to MP3, optinally including/adding metadata

Usage = {basename(__file__)} FILE [OPTION...]

Creates an 64kb/s mono MP3 file in the current working directory. If specified,
CUE markers in the WAV file will be turned into ID3 chapters in the MP3.\

Options:
    --podcast-name NAME
                    The name of the podcast, will be used in the "artist" tag
    --episode-title TITLE
                    The title for the episode, will be used in the "title" tag
    --episode-number NUMBER
                    The episode number, will be used as the track number
    --include-chapters
                    Include CUE markers as chapters

-h, --help          Print this message and exit
    --version       Print version information and exit

Requires `lame`\
"""

def main() -> None:
    args = __configure_args()

    wave_file = WaveFile(args.input)
    if args.include_chapters:
        chapters_data: List[Tuple[int, int, str]] = wave_file.read_chapters()

    print("Encoding...")
    audio_data: BytesIO = encode(wave_file)
    wave_file.close()

    tags = id3.ID3()

    if args.podcast_name:
        add_podcast_name(tags, args.podcast_name)

    if args.episode_number:
        add_episode_number(tags, args.episode_number)

    if args.episode_title:
        add_episode_title(tags, args.episode_title)

    if args.include_chapters:
        add_chapters(tags, chapters_data)

    tags.save(audio_data)

    with open(args.output, "wb") as file:
        file.write(audio_data.getvalue())


def encode(wav_file: WaveFile) -> BytesIO:
    num_cpu: int = os.cpu_count() if not None else 4
    bit_depth: int = wav_file.get_bit_depth()
    sample_rate: int = wav_file.get_sample_rate()
    num_samples: int = wav_file.get_num_samples()
    samples_per_chunk = int(__round_up(num_samples, num_cpu) / num_cpu)
    output_chunks: List[BytesIO] = list()
    threads: List[Thread] = list()

    for i in range(num_cpu):
        wav_file.set_pos(samples_per_chunk * i)
        chunk: bytes = wav_file.read_samples(samples_per_chunk)
        output_chunk = BytesIO()
        output_chunks.append(output_chunk)
        threads.append(Thread(
            target=__encode_chunk,
            name=f"Encoder {i}",
            args=(chunk, output_chunk, bit_depth, sample_rate)))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    output_bytes = BytesIO()
    for c in output_chunks:
        output_bytes.write(c.getvalue())
        c.close()

    return output_bytes


def add_podcast_name(tags: id3.ID3, name: str) -> None:
    tags.add(id3.TPE1(encoding=id3.Encoding.LATIN1, text=name))


def add_episode_title(tags: id3.ID3, episode_name: str) -> None:
    tags.add(id3.TIT2(encoding=id3.Encoding.LATIN1, text=episode_name))


def add_episode_number(tags: id3.ID3, episode_number: int) -> None:
    tags.add(id3.TRCK(encoding=id3.Encoding.LATIN1, text=str(episode_number)))


def add_chapters(tags: id3.ID3, chapters: List[Tuple[int, int, str]]) -> None:
    toc = [f"chp{index}" for index in range(len(chapters))]
    tags.add(
        id3.CTOC(encoding=id3.Encoding.LATIN1, element_id="toc",
            flags=id3.CTOCFlags.TOP_LEVEL | id3.CTOCFlags.ORDERED,
            child_element_ids=toc, sub_frames=[])
    )

    for idx, chapter in enumerate(chapters):
        tags.add(
            id3.CHAP(encoding=id3.Encoding.LATIN1, element_id=f"chp{idx}",
            start_time=chapter[0], end_time=chapter[1],
            sub_frames=[id3.TIT2(encoding=id3.Encoding.LATIN1, text=chapter[2])])
        )


def __encode_chunk(chunk: bytes, output: BytesIO, bit_depth: int, sample_rate: int) -> None:
    command: List[str] = ['lame',
                          '-r',
                          '-m', 'm',
                          '--bitwidth', str(bit_depth),
                          '-s', str(sample_rate),
                          '-']
    process: Popen = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    mp3_data: bytes = process.communicate(chunk)[0]
    output.write(mp3_data)


def __round_up(num: int, target_mutliple: int) -> int:
    while num % target_mutliple != 0:
        num += 1

    return num


def __configure_args() -> Any:
    parser = ArgumentParser(add_help=False)
    parser.add_argument("input", nargs="?")
    parser.add_argument("--podcast-name", metavar="NAME")
    parser.add_argument("--episode-title", metavar="TITLE")
    parser.add_argument("--episode-number", metavar="NUMBER")
    parser.add_argument("--include-chapters", action="store_true")

    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("--version", action="store_true")

    args = parser.parse_args()

    if args.version:
        print(version)
        exit()

    if args.help:
        print(help)
        exit()

    if not args.input:
        exit(f"Missing argument: input. Try `{basename(__file__)} --help` for more information")

    print("Verifying tools...")
    command=["lame", "--version"]
    try:
        run(command, stdout=DEVNULL, stderr=DEVNULL).check_returncode()
    except:
        exit(f"`{command[0]} not found")


    if not os.path.exists(args.input):
            exit(f"Input doesn't exist: {args.input}")

    if os.path.isdir(args.input):
            exit(f"Input cannot be a directory: {args.input}")

    args.output = __default_output(args.input)
    if os.path.exists(args.output):
        exit(f"Output file exists: {args.output}")

    return args


def __default_output(input_file: str) -> str:
    return os.path.splitext(os.path.basename(input_file))[0] + ".mp3"


if __name__ == "__main__":
    main()
