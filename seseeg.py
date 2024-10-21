#!/usr/bin/env python3
"""seseeg - EEG speech entrainment study EEG analysis tool."""

import argparse
import biosemi

# Define functions.
def dec_trial_id(id):
    """Decodes the trial identifier byte."""
    conds = (
        'typical',
        '1channel',
        '4channel'
    )
    story = (id - 128) // 12 + 1
    part = (id - 128) % 12 // 3 + 1
    cond = conds[(id - 128) % 3]
    return story, part, cond

# Define functions.
def decode(byt, f_rx, baud=512):
    """Manchester decode a data byte."""
    sym = f_rx // baud
    # Align to sync bit and calculate relative bit positions.
    ofs = byt[0][1] ^ 1
    prv, rel = byt[ofs + 1], [(2 * sym, 0)]
    for bit in byt[ofs + 2:]:
        rel.append((bit[0] - prv[0], bit[1]))
        prv = bit
    # Decode data.
    data, dat, skp, wgt = 0, 0, 0, 1
    for ele in rel:
        if ele[0] >= sym - 1 and ele[0] <= sym + 1:
            skp ^= 1
            if skp == 0:
                data += dat * wgt
                wgt <<= 1
        elif ele[0] >= 2 * sym - 1 and ele[0] <= 2 * sym + 1:
            dat ^= 1
            data += dat * wgt
            wgt <<= 1
    # Return position if sync valid, restore and return data byte.
    pos = byt[ofs][0] if data & 1 else None
    return pos, data >> 1

# Instance and configure a command line argument parser.
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--ipfile', default='eeg/seseeg.bdf',
                    help='input filename (default eeg/seseeg.bdf)')

# Parse command line arguments.
args = parser.parse_args()

# Open and parse EEG data file.
with biosemi.BdfFile(args.ipfile) as bdf:
    print(f'Processing file {args.ipfile} ...')
    # Extract bit transitions from records.
    end = bdf.nof_records * bdf.nof_samples[bdf.nof_channels - 1]
    record = bdf.trigstat
    prv = record[0] & 1
    pos, idx, bits = 1, 1, []
    while pos < end:
        if idx == len(record):
            # Buffer consumed, read next record.
            record = bdf.trigstat
            idx = 0
        nxt = record[idx] & 1
        idx += 1
        if prv != nxt:
            # State has changed, append bit.
            bits.append((pos, nxt))
        prv = nxt
        pos += 1

    print(f'Found {len(bits)} bit transitions. Grouping ...')
    # Group bit transitions into bytes.
    fs = bdf.nof_samples[bdf.nof_channels - 1] // bdf.duration
    intra = 20 * (fs // 512 + 1)    # Maximum of 20 bit transiitions in a byte.
    sync = bits[0]
    byts, byt = [], [sync]
    for bit in bits[1:]:
        if bit[0] - sync[0] <= intra:
            # Adjacent bit, append to byte.
            byt.append(bit)
        else:
            # Non-adjacent bit, begin new byte.
            byts.append(byt)
            sync = bit
            byt = [sync]

    print(f'Found {len(byts)} bytes. Decoding ...')
    # Decode and display id byte.
    story, part, cond = dec_trial_id(decode(byts[0], fs)[1])
    print(f'stimuli = story-{story}_part-{part}_{cond}.mp4')
    # Decode timestamp bytes and display timing measurements.
    beg, end = decode(byts[1], fs), decode(byts[-1], fs)
    teeg, taud = (end[0] - beg[0]) / fs, end[1] - beg[1]
    drift, ratio = 1e3 * (teeg - taud), taud / teeg
    print(f'first ts = {beg[1]} s @ EEG samp {beg[0]}, final ts = {end[1]} s')
    print(f'drift = {drift:.3f} ms, ratio = {ratio:.7f}')
