import sys
import os
import shutil
from glob import glob
import mutagen
from mutagen.id3 import ID3, CHAP, CTOC, APIC, TIT2, PictureType, CTOCFlags


def _get_frames(f_id: str):
    paths = glob(f'{f_id}/*.jpg')
    for path in paths:
        name = os.path.basename(path)
        timestamp = int(os.path.splitext(name)[0])
        yield timestamp, path


def _get_chapters(frames, length_ms):
    for i, (timestamp, path) in enumerate(frames):
        end_time = frames[i + 1][0] if i + 1 < len(frames) else length_ms
        with open(path, 'rb') as pic:
            apic = APIC(
                type=PictureType.OTHER,
                mime='image/jpeg',
                data=pic.read()
            )
        tit2 = TIT2(text=f'Chapter {i + 1}')
        yield CHAP(
            element_id=f'chp{i}',
            start_time=timestamp,
            end_time=end_time,
            sub_frames=[apic, tit2]
        )


def chapterize(mp3_path, frames_path, outfile):
    shutil.copyfile(mp3_path, outfile)

    infile = mutagen.File(mp3_path)
    length_ms = int(infile.info.length * 1000)

    tag = ID3(mp3_path)

    frames = sorted(_get_frames(frames_path))

    if (len(frames) > 255):
        print(f'{mp3_path}: too many frames ({len(frames)} > 255); not chapterizing',
              file=sys.stderr)
        return

    chapters = list(_get_chapters(frames, length_ms))
    toc = CTOC(
        element_id='toc',
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=[ch.element_id for ch in chapters],
    )

    tag.add(toc)
    for ch in chapters:
        tag.add(ch)

    tag.save(outfile)


def main():
    mp3_path, frames_path, outfile = sys.argv[1:4]
    chapterize(mp3_path, frames_path, outfile)


if __name__ == '__main__':
    main()
