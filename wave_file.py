import wave
import collections
import struct
from typing import List, Tuple, Dict, IO

class WaveFile:
    def __init__(self, path: str) -> None:
        self.path: str = path
        self.wav_file: wave.Wave_read = wave.open(path, "rb")


    def read_chapters(self) -> List[Tuple[int, int, str]]:
        with open(self.path, "rb") as fid:
            fsize: int = self.__read_riff_chunk(fid)
            markersdict: Dict[int, Dict[str, str]] = collections.defaultdict(
                lambda: {"timestamp": "", "label": ""})

            while (fid.tell() < fsize):
                chunk_id: bytes = fid.read(4)
                if chunk_id == b"cue ":
                    str1: bytes = fid.read(8)
                    numcue: int = struct.unpack('<ii', str1)[1]
                    for _ in range(numcue):
                        str1 = fid.read(24)
                        cue_id, position = struct.unpack("<iiiiii", str1)[0:2]
                        markersdict[cue_id]["timestamp"] = str(
                            self.__samples_to_millis(position))
                elif chunk_id == b"LIST":
                    fid.read(8)
                elif chunk_id == b"labl":
                    str1 = fid.read(8)
                    size, cue_id = struct.unpack("<ii", str1)
                    size = size + (size % 2)
                    label: bytes = fid.read(size-4).rstrip(b"\x00")
                    markersdict[cue_id]["label"] = label.decode("utf-8")
                else:
                    self.__skip_unknown_chunk(fid)

        sorted_markers: List[Dict[str, str]] = sorted(
            [markersdict[l] for l in markersdict],
            key=lambda k: int(k["timestamp"]))

        ret: List[Tuple[int, int, str]] = list()
        num_chapters: int = len(sorted_markers)
        for idx, chap in enumerate(sorted_markers):
            if (idx + 1 < num_chapters):
                next_timestamp = int(sorted_markers[idx + 1]["timestamp"])
            else:
                next_timestamp = self.__samples_to_millis(self.get_num_samples())

            ret.append((int(chap["timestamp"]), next_timestamp, chap["label"]))

        return ret


    def read_samples(self, num: int) -> bytes:
        return self.wav_file.readframes(num)


    def get_num_samples(self) -> int:
        return self.wav_file.getnframes()


    def set_pos(self, pos: int) -> None:
        self.wav_file.setpos(pos)


    def get_bit_depth(self) -> int:
        return self.wav_file.getsampwidth() * 8


    def get_sample_rate(self) -> int:
        return self.wav_file.getframerate()


    def close(self) -> None:
        self.wav_file.close()


    def __skip_unknown_chunk(self, fid: IO[bytes]) -> None:
        data = fid.read(4)
        size = struct.unpack('<i', data)[0]
        if bool(size & 1):
            size += 1

        fid.seek(size, 1)


    def __read_riff_chunk(self, fid: IO[bytes]) -> int:
        str1: bytes = fid.read(4)
        if str1 != b'RIFF':
            raise ValueError("Not a WAV file.")

        fsize: int = struct.unpack('<I', fid.read(4))[0] + 8
        str1 = fid.read(4)
        if (str1 != b'WAVE'):
            raise ValueError("Not a WAV file.")

        return fsize


    def __samples_to_millis(self, samples: int) -> int:
        return int((samples / self.get_sample_rate()) * 1000)