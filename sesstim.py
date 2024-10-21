#!/usr/bin/env python3
"""sesstim - EEG speech entrainment study stimuli generation tool."""

import os
import argparse
import numpy as np

from scipy.io import wavfile
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.video.io.VideoFileClip import VideoFileClip

# Define functions.
def enc_trial_id(story, part, cond):
    """Encode a trial identifier byte."""
    ccodes = {
        'typical': 0,
        '1channel': 1,
        '4channel': 2
    }
    return 128 + 12 * (story - 1) + 3 * (part - 1) + ccodes[cond]

def encode(data, f_tx, baud=512):
    """Manchester encode a data byte."""
    A = np.pi / 4               # Max amplitude for Fourier-summed square wave.
    sym = int(np.ceil(f_tx / baud))
    zero = np.concatenate((-A * np.ones(sym), A * np.ones(sym)))
    one = np.concatenate((A * np.ones(sym), -A * np.ones(sym)))
    buffer = np.concatenate((one, one, np.zeros(8 * 2 * sym)))
    for n in range(2, 10):
        buffer[2 * sym * n:2 * sym * (n + 1)] = one if data & 1 else zero
        data >>= 1
    return sym, buffer

# Instance and configure a command line argument parser.
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--ipath', default='audio/',
                    help='audio input file directory (default audio/)')
parser.add_argument('-o', '--opath', default='video/',
                    help='video output file directory (default video/)')
parser.add_argument('-v', '--video', default='video/EEG_disappearing_fixation_95s.mp4',
                    help='video clip file path (default video/EEG_disappearing_fixation_95s.mp4')

# Parse command line arguments.
args = parser.parse_args()

# Iterate over audio files in the input directory.
for audiofile in os.listdir(args.ipath):
    # Read audio data.
    fps, audio = wavfile.read(args.ipath + audiofile)
    # Convert audio data to native floating point type in the interval (1.0, -1.0].
    if audio.dtype != 'float32':
        audio = audio / np.iinfo(audio.dtype).max
    # Split audio filename.
    split = audiofile.removesuffix('.wav').split('_')
    story, part, cond = int(split[1]), int(split[3]), split[4]
    # Synthesise ident data.
    nedge, ident = encode(enc_trial_id(story, part, cond), fps)
    nlead = int(0.1 * fps)          # 100 ms lead in.
    nbyte = ident.size              # Nof samples in a byte.
    # Allocate trigger buffer.
    trigs = np.concatenate((np.zeros(nlead), ident, np.zeros(audio.size - nlead - nbyte)))
    # Synthesise timestamp data.
    nstamps = (audio.size - nbyte) // fps
    for n in range(1, nstamps + 1):
        i = n * fps - nedge
        nedge, trigs[i:i + nbyte] = encode(n, fps)
    # Read video data.
    videoclip = VideoFileClip(args.video)
    # Cut video to audio length in optimal window.
    t_blank = 3     # Amination ends 3 s before the video ends.
    t_start, t_end = videoclip.duration - audio.size / fps - t_blank, videoclip.duration - t_blank
    if t_start < 0:
        t_end -= t_start
        t_start = 0
    videoclip = videoclip.subclip(t_start, t_end)
    # Embed audio and trigger data.
    videoclip = videoclip.set_audio(AudioArrayClip(np.vstack((audio, trigs)).T, fps=fps))
    # Generate video name string.
    videoname = f'story-{story}_part-{part}_{cond}.mp4'
    # Write video and audio output.
    videoclip.write_videofile(args.opath + videoname, audio_fps=fps, audio_bitrate='256k')
    # Clean up.
    videoclip.close()
