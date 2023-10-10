import sys
import os
import shutil
import json
from glob import glob
import mutagen
from mutagen.id3 import (ID3, CHAP, CTOC, APIC, TIT2, TLEN, TENC,
                         PictureType, CTOCFlags)

# Monkey patch to ensure chapter order
# https://github.com/quodlibet/mutagen/pull/539
from mutagen.id3._tags import ID3Tags, save_frame


def _write(self, config):
    # Sort frames by 'importance', then reverse frame size and then frame
    # hash to get a stable result
    order = ["TIT2", "TPE1", "TRCK", "TALB", "TPOS", "TDRC", "TCON"]

    framedata = [
        (f, save_frame(f, config=config)) for f in self.values()]

    def get_prio(frame):
        try:
            return order.index(frame.FrameID)
        except ValueError:
            return len(order)

    def sort_key(items):
        frame, data = items
        frame_key = frame.HashKey
        frame_size = len(data)

        # Let's ensure chapters are always sorted by their 'start_time'
        # and not by size/element_id pair.
        if frame.FrameID == "CHAP":
            frame_key = frame.FrameID
            frame_size = frame.start_time

        return (get_prio(frame), frame_size, frame_key)

    framedata = [d for (f, d) in sorted(framedata, key=sort_key)]

    # only write unknown frames if they were loaded from the version
    # we are saving with. Theoretically we could upgrade frames
    # but some frames can be nested like CHAP, so there is a chance
    # we create a mixed frame mess.
    if self._unknown_v2_version == config.v2_version:
        framedata.extend(data for data in self.unknown_frames
                         if len(data) > 10)

    return bytearray().join(framedata)


ID3Tags._write = _write


def _get_frames(f_id: str):
    paths = glob(f'{f_id}/*.jpg')
    for path in paths:
        name = os.path.basename(path)
        timestamp = int(os.path.splitext(name)[0])
        yield timestamp, path


def _find_title(start, end, chapter_annotations):
    closest = next(
        iter(
            sorted((a for a in chapter_annotations),
                   key=lambda a: abs(start - a['start_time'] * 1000))
        ),
        None
    )
    return closest['title'] if closest else None


def _get_chapters(frames, length_ms, chapter_annotations):
    for i, (timestamp, path) in enumerate(frames):
        start_time = 0 if i == 0 else timestamp
        end_time = frames[i + 1][0] if i + 1 < len(frames) else length_ms
        title = _find_title(start_time, end_time, chapter_annotations)
        with open(path, 'rb') as pic:
            apic = APIC(
                type=PictureType.OTHER,
                mime='image/jpeg',
                data=pic.read()
            )
        tit2 = TIT2(text=title or f'Chapter {i + 1}')
        yield CHAP(
            element_id=f'chp{i}',
            start_time=start_time,
            end_time=end_time,
            sub_frames=[tit2, apic]
        )


def chapterize(mp3_path, frames_path, infojson_path, outfile):
    shutil.copyfile(mp3_path, outfile)

    infile = mutagen.File(mp3_path)
    length_ms = int(infile.info.length * 1000)

    tag = ID3(mp3_path, v2_version=3)

    frames = sorted(_get_frames(frames_path))

    if (len(frames) > 255):
        print(f'{mp3_path}: too many frames ({len(frames)} > 255); not chapterizing',
              file=sys.stderr)
        return

    with open(infojson_path, encoding='utf8') as f:
        infojson = json.load(f)

    chapters = list(_get_chapters(
        frames,
        length_ms,
        infojson['chapters'] or [],
    ))
    toc = CTOC(
        element_id='toc',
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=[ch.element_id for ch in chapters],
    )

    tag.add(toc)
    for ch in chapters:
        tag.add(ch)

    tag.add(TLEN(text=str(length_ms)))
    tag.add(TENC(text='chapterize.py'))

    tag.delall('TXXX')
    tag.delall('TSSE')

    tag.save(outfile, v2_version=3)


def main():
    mp3_path, frames_path, infojson_path, outfile = sys.argv[1:5]
    chapterize(mp3_path, frames_path, infojson_path, outfile)


if __name__ == '__main__':
    main()
