"""Whisper output post-processing — drop hallucinations + glue word splits."""
HALLUC_FRAGMENTS = {
    "ご視", "聴", "ご視聴", "ご視聴ありがとうございました",
    "ありがとうございました。", "ありがとうございました",
}
TERMINATORS = set("。.?？!！」』")


def process(segs: list[dict]) -> list[dict]:
    if not segs:
        return []

    # Step 1: drop the initial ご視聴 hallucination run (only at start)
    while segs and segs[0]["text"] in HALLUC_FRAGMENTS \
            and segs[0]["start"] < 70:
        segs.pop(0)

    # Step 2: drop ≤1-char segments stretched > 4s (artifact filler)
    pruned = [s for s in segs
              if not (len(s["text"]) <= 1 and (s["end"] - s["start"]) > 4.0)]

    # Step 3: merge tight word-internal splits (gap < 0.05s, prev not terminator)
    glued: list[dict] = []
    for s in pruned:
        if glued:
            prev = glued[-1]
            gap = s["start"] - prev["end"]
            prev_done = bool(prev["text"]) and prev["text"][-1] in TERMINATORS
            if gap < 0.05 and not prev_done:
                prev["text"] = prev["text"] + s["text"]
                prev["end"] = s["end"]
                continue
        glued.append(dict(s))

    # Step 4: de-dup consecutive identical text within 0.5 s
    deduped: list[dict] = []
    for s in glued:
        if deduped and deduped[-1]["text"] == s["text"] \
                and s["start"] - deduped[-1]["end"] < 0.5:
            deduped[-1]["end"] = s["end"]
        else:
            deduped.append(s)

    return deduped
