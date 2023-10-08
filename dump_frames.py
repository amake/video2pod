import sys
from mutagen.id3 import ID3


def dump(mp3_path):
    tag = ID3(mp3_path)
    for frame in tag.values():
        print(frame.pprint())


def main():
    mp3_path = sys.argv[1]
    dump(mp3_path)


if __name__ == '__main__':
    main()
