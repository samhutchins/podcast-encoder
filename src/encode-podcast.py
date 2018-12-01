#!/usr/bin/env python3.6

import struct
import collections
import os
from wave_file import WaveFile
from argparse import ArgumentParser, Namespace
from subprocess import Popen, PIPE
from threading import Thread
from io import BytesIO
from mutagen import id3
from typing import Tuple, List, IO, Dict, Any


def __main() -> None:
    args = __configure_args()

    wave_file = WaveFile(args.input)
    if args.include_chapters:
        chapters_data: List[Tuple[int, int, str]] = wave_file.read_chapters()

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
    parser = ArgumentParser(description="Encode wav files to MP3")
    parser.add_argument("input", help="A `wav` file to transcode")
    parser.add_argument("-o", "--output", help="Path to output file")
    parser.add_argument("--podcast-name", type=str, help="The name of the podcast")
    parser.add_argument("--episode-title", type=str, help="The title of the episode")
    parser.add_argument("--episode-number", type=str, help="Episode number")
    parser.add_argument("--include-chapters", action="store_true", help="Convert cue markers to MP3 chapters")

    args: Any = parser.parse_args()

    if not args.output:
        args.output = __default_output(args.input)

    return args


def __default_output(input_file: str) -> str:
    return os.path.splitext(os.path.basename(input_file))[0] + ".mp3"


if __name__ == "__main__":
    __main()
