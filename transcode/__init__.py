from gevent import monkey, spawn
monkey.patch_all()
from argparse import ArgumentParser
from gevent.subprocess import Popen, PIPE, DEVNULL, check_output
import os
import json


def get_duration(filename):
    ffprobe = ['ffprobe', '-v', 'error', '-show_format',
               '-print_format', 'json', filename]
    data = json.loads(check_output(ffprobe).decode())
    return float(data['format']['duration']) * 1e6


def transcode(infile, outfile, metadata=None, done_callback=None, progress_callback=None):
    ffmpeg = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y',
              '-progress', '-', '-i', infile, '-codec:v', 'h264',
              '-codec:a', 'aac', '-strict', '-2', outfile]
    if metadata:
        for key, value in metadata.items():
            ffmpeg[-1:1] = ['-metadata', '{}={}'.format(key, value)]

    out = PIPE if progress_callback else DEVNULL
    with Popen(ffmpeg, stdout=out) as process:
        if not progress_callback:
            process.wait()
            if done_callback:
                done_callback()
            return
        duration = get_duration(infile)
        while process.poll() is None:
            for line in iter(process.stdout.readline, b''):
                if b'out_time_ms' in line:
                    out_time_ms = int(line[12:])
                    percent = out_time_ms / duration * 100
                    progress_callback(percent)
        progress_callback(100)
    if done_callback:
        done_callback()


def from_cmd_line():
    parser = ArgumentParser()
    parser.add_argument('infile')
    parser.add_argument('outfile')
    parser.add_argument('-t', '--metadata-title')
    args = parser.parse_args()

    def progress_callback(percent):
        print('\r[{0:50s}] {1:.1f}%'.format('#' * round(percent / 2), percent), sep='', end='', flush=True)

    def done_callback():
        print('\nDone')

    print('Transcoding {} to {}...'.format(args.infile, args.outfile))
    metadata = dict(title=os.path.basename(os.path.splitext(args.outfile)[0]))
    if args.metadata_title:
        metadata['title'] = args.metadata_title
    proc = spawn(transcode, args.infile, args.outfile, metadata, done_callback, progress_callback)
    try:
        proc.join()
    except KeyboardInterrupt:
        proc.kill()


class Transcoder(object):
    pass

if __name__ == '__main__':
    from_cmd_line()

