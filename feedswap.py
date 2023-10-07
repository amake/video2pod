import sys
import os
import urllib.request
from lxml import etree
from yt_dlp import YoutubeDL
import editdistance
from configparser import ConfigParser


def load_config(config_file):
    if not os.path.isfile(config_file):
        print('No config file found. Please create one.')
        exit(1)
    c = ConfigParser()
    c.read(config_file)
    return c


config = load_config('config.ini')
pod_url = config['upstream']['podcast_feed_url']
video_url = config['upstream']['video_playlist_url']
enclosure_url_format = config['deployment']['enclosure_url_format']


def _get_videos(url):
    channel = (YoutubeDL({'extract_flat': 'in_playlist', 'quiet': True})
               .extract_info(video_url, download=False))
    for video in channel['entries']:
        yield (video['title'], video['id'])


def _find_closest_match(needle, haystack, key: lambda x: x):
    exact = next((h for h in haystack if needle in key(h)), None)
    if exact is not None:
        return exact

    dist, fuzzy = min((editdistance.eval(needle, key(h)), h) for h in haystack)
    if dist > 4:
        return None
    return fuzzy


def feedswap(known_ids):
    with urllib.request.urlopen(pod_url) as response:
        raw_xml = response.read()
    xml = etree.fromstring(raw_xml)

    videos = list(_get_videos(video_url))

    for item in xml.xpath('//item'):
        title = item.xpath('title')[0].text
        enclosure = item.xpath('enclosure')[0]

        ep_no = title.split(':')[0] if ':' in title else title
        m = _find_closest_match(ep_no, videos, key=lambda x: x[0])
        if m is None:
            continue

        v_id = m[1]
        if v_id not in known_ids:
            continue
        enclosure.attrib['url'] = enclosure_url_format % f'{v_id}.mp3'

    print(etree.tounicode(xml, pretty_print=True))


def main():
    known_ids = sys.argv[1:]
    feedswap(known_ids)


if __name__ == '__main__':
    main()
