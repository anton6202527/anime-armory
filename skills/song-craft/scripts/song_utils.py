import array
import math
import re
import wave

# Common regular expressions for lyric parsing
PLACEHOLDER = re.compile(r"待精修|待填|待定|占位|歌词…|歌词\.\.\.|placeholder|TODO|（待|\(待")
SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
# Character count regex: includes CJK characters and alphanumerics, ignores punctuation
COUNT_RE = re.compile(r"[0-9A-Za-z一-鿿぀-ヿ]")
STAGE_DIR = re.compile(r"^\s*[（(].*[）)]\s*$")


def line_chars(s):
    """Return the number of singable characters in a lyric line."""
    return len(COUNT_RE.findall(s))


def parse_seconds(value):
    """Parse a duration value into seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = re.search(r"(\d+)", str(value))
    return int(m.group(1)) if m else None


def extract_last_word(line):
    """Extract the last word/character for rhyme analysis."""
    clean = re.sub(r"[^\w\s一-鿿぀-ヿ]+$", "", line.strip())
    if not clean:
        return ""
    match = re.search(r"([0-9A-Za-z]+|[一-鿿぀-ヿ])$", clean)
    return match.group(1) if match else clean[-1]


def get_rhyme_vowel(char, has_pypinyin, pypinyin_module):
    """Get the rhyme vowel for a given character using pypinyin if available."""
    if not has_pypinyin or not re.match(r"[一-鿿]", char):
        return char
    
    pys = pypinyin_module.pinyin(char, style=pypinyin_module.Style.NORMAL)
    if not pys:
        return char
    py = pys[0][0]
    
    vowels = ["ang", "eng", "ing", "ong", "an", "en", "in", "un", "ao", "ou", "ai", "ei", "ui", "ao", "ou", "iu", "ie", "ve", "er", "a", "o", "e", "i", "u", "v"]
    for v in vowels:
        if py.endswith(v):
            return v
    return py[-1] if py else char


def _wav_peak_clip(path, clip_thresh=0.995, silence_dbfs=-40.0):
    """Return basic amplitude metrics for a WAV file.
    Raises wave.Error or EOFError if unparsable.
    Returns: (dur, rate, ch, sw, peak_ratio, clip_ratio, rms_ratio, head_silence, tail_silence)
    """
    with wave.open(path, "rb") as w:
        ch, sw, rate, nframes = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        dur = nframes / rate if rate else 0.0
        if sw != 2:
            return dur, rate, ch, sw, None, None, None, None, None
            
        frames = w.readframes(nframes)
        a = array.array("h")
        a.frombytes(frames)
        
        peak = 0
        clipped = 0
        total = len(a)
        full = 32768
        thr = int(clip_thresh * full)
        sq = 0
        
        for v in a:
            av = -v if v < 0 else v
            if av > peak:
                peak = av
            if av >= thr:
                clipped += 1
            sq += v * v
            
        peak_ratio = peak / full if full else 0.0
        clip_ratio = clipped / total if total else 0.0
        rms_ratio = math.sqrt(sq / total) / full if total else 0.0
        
        silent_thr = int((10 ** (silence_dbfs / 20.0)) * full)
        head = 0
        for v in a:
            if abs(v) > silent_thr:
                break
            head += 1
            
        tail = 0
        for v in reversed(a):
            if abs(v) > silent_thr:
                break
            tail += 1
            
        samples_per_second = rate * ch if rate and ch else 1
        return (
            dur, rate, ch, sw, 
            peak_ratio, clip_ratio, rms_ratio, 
            head / samples_per_second, tail / samples_per_second
        )
