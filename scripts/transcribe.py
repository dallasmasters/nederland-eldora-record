"""Transcribe Board of Trustees meeting videos (Town of Nederland YouTube channel) with whisper.cpp.

Pass 1 (default): every listed meeting with small.en, writing transcripts/<date>_<video id>.json (whisper.cpp JSON with
timestamps) and .txt. Pass 2 (--pass2 FILE): re-run the time ranges listed in FILE (lines "video_id start_s end_s")
with large-v3-turbo for accurate quotes, writing transcripts/pass2/<video id>_<start>-<end>.json.

Audio is cached in video/audio/ (not in git). Finished files are skipped, so the run can be restarted.
Transcripts are unofficial; the Town's videos are the record.

  python3 scripts/transcribe.py            # pass 1, all meetings
  python3 scripts/transcribe.py --pass2 transcripts/pass2_ranges.txt
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, 'video', 'audio')
OUT = os.path.join(ROOT, 'transcripts')
MODELS = '/usr/local/share/whisper-cpp/ggml-{}.bin'
THREADS = '8'
LOG = os.path.join(ROOT, 'video', 'transcribe.log')
# YouTube sometimes refuses downloads for a while (HTTP 403). Wait and retry instead of stopping the run.
RETRY_WAITS = [5 * 60, 10 * 60, 20 * 60]   # seconds before the 2nd, 3rd, and 4th attempts
PAUSE = 60                                 # seconds between downloads

# Meetings with Board actions on the acquisition (analysis/eldora_votes.csv) plus the July 2025 town hall.
# (meeting date, [video ids in order], note). Video ids from the Town channel listing (video/channel.tsv).
MEETINGS = [
    ('2025-01-07', ['F3Kb-cwTvS8'], 'Northland ratified; Res. 2025-03'),
    ('2025-01-21', ['T9IKSJ_OoZw'], 'Ord. 873, Mountain Recreation Enterprise'),
    ('2025-03-18', ['Ljv-NvUCrt8'], 'water-court executive session'),
    ('2025-04-15', ['xKnXR7OjDwo'], 'Res. 2025-08, J.P. Morgan'),
    ('2025-05-20', ['m0IScYz4IKE'], 'Res. 2025-11 (video titled May 22)'),
    ('2025-07-10', ['0AigDgranLU'], 'Board town hall'),
    ('2025-07-15', ['yAJn-0ifXlk'], 'Res. 2025-15, SE Group'),
    ('2025-08-05', ['ZgJBnuhE0-0'], 'Res. 2025-16, 2025-17'),
    ('2025-09-02', ['Xs-07zuAVw8'], 'Res. 2025-19'),
    ('2025-10-07', ['3NtGCQUB8YY'], 'Res. 2025-22'),
    ('2026-01-06', ['WkgdzanY1IM'], 'Ord. 882, purchase agreement'),
    ('2026-01-20', ['iFH8e_nZnWc', 'J__yBhAQu10'], 'Ord. 885, bonds'),
    ('2026-03-17', ['9qQh_WAjj8E', 'wTIek1RbLIE'], 'Res. 2026-07'),
    ('2026-03-31', ['mlxwy88Kt0M'], 'Ikon agreement (special meeting)'),
    ('2026-04-21', ['6jQN1SbWuQY', 'CE5L6KNdjXk'], 'Res. 2026-12, 2026-13'),
    ('2026-07-07', ['bm_DSuMnc-M'], 'Stifel; resident questions'),
]

# Names and terms the model otherwise mishears; whisper.cpp uses this as context.
PROMPT = ('Nederland Board of Trustees meeting. Mayor Sterling, Mayor Pro Tem Miller, Trustees Giblin, Larsen, Maris, '
          'Corvalan, Joslin, Tye, Dewart, Donahue, Kennedy. Town Manager Jon Cain, Town Clerk Macy Caligaris, '
          'Town Attorney Jennifer Madsen. Eldora Mountain Resort, POWDR, Alterra, Ikon Pass, Mountain Recreation '
          'Enterprise, CSAFE, Plante Moran, Stifel, SE Group, Kline Alvarado Veio, Hogan Lovells, Dickinson Wright, '
          'Widner Juran, Northland Securities, J.P. Morgan, warrants, executive session, ordinance, resolution.')


def log(msg):
    line = f'{time.strftime("%Y-%m-%d %H:%M:%S")} {msg}'
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')


def audio(vid):
    """Download a video's audio once and convert it to 16 kHz mono WAV for whisper.cpp."""
    wav = os.path.join(AUDIO, vid + '.wav')
    if not os.path.exists(wav):
        m4a = os.path.join(AUDIO, vid + '.m4a')
        if not os.path.exists(m4a):
            download(vid)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', m4a, '-ar', '16000', '-ac', '1', wav], check=True)
    return wav


def download(vid):
    cmd = ['yt-dlp', '-q', '-f', 'bestaudio', '-x', '--audio-format', 'm4a',
           '-o', os.path.join(AUDIO, '%(id)s.%(ext)s'), f'https://www.youtube.com/watch?v={vid}']
    for attempt, wait in enumerate([0] + RETRY_WAITS, 1):
        if wait:
            log(f'download of {vid} failed; retrying in {wait // 60} min (attempt {attempt} of {len(RETRY_WAITS) + 1})')
            time.sleep(wait)
        if subprocess.run(cmd).returncode == 0:
            time.sleep(PAUSE)
            return
    raise RuntimeError(f'download of {vid} failed after {len(RETRY_WAITS) + 1} attempts')


def whisper(model, wav, out_base, offset_ms=0, duration_ms=0):
    # -mc 0: don't carry decoded text forward. With the default, whisper.cpp got stuck after a long silent lead-in
    # (e.g., while the Board was in executive session) and marked 25-50 minutes of speech as [BLANK_AUDIO].
    cmd = ['whisper-cli', '-m', MODELS.format(model), '-t', THREADS, '-f', wav, '--prompt', PROMPT, '-mc', '0',
           '-oj', '-otxt', '-of', out_base, '-np']
    if offset_ms:
        cmd += ['-ot', str(offset_ms)]
    if duration_ms:
        cmd += ['-d', str(duration_ms)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pass1():
    os.makedirs(OUT, exist_ok=True)
    for date, vids, note in MEETINGS:
        for vid in vids:
            base = os.path.join(OUT, f'{date}_{vid}')
            if os.path.exists(base + '.json'):
                continue
            t0 = time.time()
            log(f'start {date} {vid} ({note})')
            try:
                wav = audio(vid)
            except RuntimeError as err:   # skip it; a later run picks it up
                log(f'skipped {date} {vid}: {err}')
                continue
            whisper('small.en', wav, base)
            log(f'done  {date} {vid} in {(time.time() - t0) / 60:.0f} min')
    missing = [v for d, vids, _ in MEETINGS for v in vids if not os.path.exists(os.path.join(OUT, f'{d}_{v}.json'))]
    log('pass 1 complete' + (f'; not yet transcribed: {", ".join(missing)} (rerun to retry)' if missing else ''))


def pass2(ranges_file):
    out = os.path.join(OUT, 'pass2')
    os.makedirs(out, exist_ok=True)
    for line in open(ranges_file):
        if not line.strip() or line.startswith('#'):
            continue
        vid, start, end = line.split()[:3]
        base = os.path.join(out, f'{vid}_{start}-{end}')
        if os.path.exists(base + '.json'):
            continue
        t0 = time.time()
        log(f'pass2 start {vid} {start}-{end}')
        whisper('large-v3-turbo', audio(vid), base, int(float(start) * 1000), int((float(end) - float(start)) * 1000))
        log(f'pass2 done  {vid} {start}-{end} in {(time.time() - t0) / 60:.0f} min')
    log('pass 2 complete')


if __name__ == '__main__':
    os.makedirs(AUDIO, exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == '--pass2':
        pass2(sys.argv[2])
    else:
        pass1()
