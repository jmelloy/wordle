"""FastAPI backend wrapping wordle_ml solver logic."""

import os
from collections import Counter, defaultdict
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Wordle ML core logic (ported from wordle_ml.py) ---

WORD_LENGTH = 5
ALPHA = "abcdefghijklmnopqrstuvwxyz"
RED_START = WORD_LENGTH * 2 * 26
YELLOW_START = WORD_LENGTH * 26


def word_vec(word):
    num_list = [0] * (26 * WORD_LENGTH) + [0] * (26 * WORD_LENGTH) + [1] * 26 * WORD_LENGTH
    for i, l in enumerate(word):
        pos = i * 26 + ALPHA.index(l)
        num_list[pos] = 1
        for j in range(WORD_LENGTH):
            if j != i and word[j] != l:
                num_list[YELLOW_START + j * 26 + ALPHA.index(l)] = 1
    for x in set(word):
        count = word.count(x)
        for j in range(count):
            num_list[RED_START + j * 26 + ALPHA.index(x)] = 0
    return np.array(num_list)


def wordle_rank(word, check):
    result = ["r"] * len(word)
    letters = list(check)
    for i, l in enumerate(word):
        if word[i] == check[i]:
            result[i] = "g"
            letters.remove(l)
    for i, l in enumerate(word):
        if result[i] == "g":
            continue
        if word[i] in check and l in letters:
            result[i] = "y"
            letters.remove(l)
    return "".join(result)


# Load word data
c = Counter()
words = {}
word_freq = {}

with open("unigram_freq.csv") as f:
    f.readline()
    for line in f:
        word, count = line.strip().split(",")
        if len(word) != WORD_LENGTH or word != word.lower():
            continue
        word_freq[word] = int(count)

with open("twl06.txt") as f:
    f.readline()
    for line in f:
        word = line.strip()
        if len(word) != WORD_LENGTH or word != word.lower():
            continue
        words[word] = word_vec(word)
        c.update(word)
        if word not in word_freq:
            word_freq[word] = 1000000

word_freq_list = list(word_freq.keys())
# Pre-build index for O(1) freq lookups
word_freq_rank = {w: i for i, w in enumerate(word_freq_list)}
letter_freq = [x[0] for x in c.most_common()]

# Pre-build word matrix for vectorized dot products
word_names = list(words.keys())
word_matrix = np.array([words[w] for w in word_names])  # shape: (n_words, vec_len)


def get_word_vec_guess(guess, result):
    num_list = [0] * (26 * WORD_LENGTH * 3)
    for i, l in enumerate(guess):
        base = i
        if result[i].lower() == "r":
            base = 2 * WORD_LENGTH
            mod = guess.count(l) - 1
            base += mod
        elif result[i].lower() == "y":
            base = WORD_LENGTH + i
        pos = base * 26 + ALPHA.index(l)
        num_list[pos] = 1
    return np.array(num_list)


def get_words(total, guess, result):
    guess_array = get_word_vec_guess(guess, result)
    total = np.logical_or(guess_array, total)

    # Vectorized: compute all dot products at once via matrix multiply
    t = total.astype(np.int8)
    greens = word_matrix[:, :YELLOW_START] @ t[:YELLOW_START]
    yellows = word_matrix[:, YELLOW_START:RED_START] @ t[YELLOW_START:RED_START]
    reds = word_matrix[:, RED_START:] @ t[RED_START:]

    matches = defaultdict(list)
    for i, name in enumerate(word_names):
        matches[(int(greens[i]), int(yellows[i]), int(reds[i]))].append(name)

    n_words = len(word_freq_rank)
    for v in matches.values():
        v.sort(key=lambda x: word_freq_rank.get(x, n_words))

    return total, matches


def get_greens(total):
    word = ["."] * WORD_LENGTH
    for i in range(0, YELLOW_START):
        if total[i] == 1:
            word[i // 26] = ALPHA[i % 26]
    return "".join(word)


def get_yellows(total):
    word = set()
    for i in range(YELLOW_START, RED_START):
        if total[i] == 1:
            word.add(ALPHA[i % 26])
    return "".join(sorted(word))


def score_word(w):
    return sum(letter_freq.index(l) for l in w)


# Compute starting suggestions - prefer words with 5 unique letters and common letters
def starter_score(w):
    unique_penalty = (5 - len(set(w))) * 50
    return score_word(w) + unique_penalty

starting_words = sorted(words.keys(), key=starter_score)[:50]

# --- API Models ---

class Guess(BaseModel):
    word: str
    result: str  # e.g. "gyrrg" - green/yellow/red per position


class SolveRequest(BaseModel):
    guesses: list[Guess]


# --- API Endpoints ---

@app.get("/api/starting-words")
def api_starting_words():
    """Return top starting word suggestions."""
    scored = [(w, score_word(w)) for w in starting_words]
    return [{"word": w, "score": s} for w, s in scored]


@app.get("/api/words")
def api_all_words():
    """Return all valid 5-letter words with frequency info."""
    return [{"word": w, "freq": word_freq.get(w, 0)} for w in sorted(words.keys())]


def compute_eliminations(candidate_list):
    """For each candidate, compute how many distinct wordle_rank partitions it creates.

    More partitions = guessing that word gives more information = eliminates more.
    This mirrors check_word() from wordle_ml.py.
    """
    # Only score the top candidates to keep it fast (n^2 with full list)
    score_limit = min(len(candidate_list), 80)
    to_score = candidate_list[:score_limit]
    eliminations = {}
    for word in to_score:
        patterns = set()
        for other in candidate_list:
            patterns.add(wordle_rank(word, other))
        eliminations[word] = len(patterns)
    return eliminations


@app.post("/api/solve")
def api_solve(req: SolveRequest):
    """Given a list of guesses with results, return remaining candidates with scores."""
    total = np.array([0] * (26 * WORD_LENGTH * 3))

    all_matches = {}
    for g in req.guesses:
        total, matches = get_words(total, g.word.lower(), g.result.lower())
        all_matches = matches

    if not all_matches:
        return {"candidates": [], "greens": ".....", "yellows": "", "total_remaining": 0}

    # Best group = most green matches, then most yellow, then most red (reds confirm excluded letters)
    best_key = sorted(all_matches.keys(), key=lambda k: (k[0], k[1], k[2]))[-1]
    candidates = all_matches[best_key]
    total_words = len(candidates)

    # Compute elimination scores for top candidates (scored against full list)
    eliminations = compute_eliminations(candidates)
    max_elim = max(eliminations.values()) if eliminations else 1

    # Build results: scored candidates first (sorted by elim), then rest by freq
    scored = []
    unscored = []
    for w in candidates:
        freq = word_freq.get(w, 0)
        elim = eliminations.get(w, 0)
        entry = {
            "word": w,
            "rank": 0,
            "freq": freq,
            "score": score_word(w),
            "eliminations": elim,
            "elim_pct": round(elim / max_elim * 100) if max_elim else 0,
        }
        if w in eliminations:
            scored.append(entry)
        else:
            unscored.append(entry)

    scored.sort(key=lambda c: (-c["eliminations"], -c["freq"]))
    result_candidates = scored + unscored
    for i, c in enumerate(result_candidates):
        c["rank"] = i + 1

    return {
        "candidates": result_candidates,
        "greens": get_greens(total),
        "yellows": get_yellows(total),
        "total_remaining": total_words,
        "match_key": list(best_key),
    }


@app.get("/api/suggest/{word}")
def api_suggest(word: str):
    """Suggest words matching a partial pattern (for autocomplete)."""
    word = word.lower()
    matches = [w for w in words if w.startswith(word)]
    matches.sort(key=lambda x: word_freq_list.index(x) if x in word_freq_list else len(word_freq_list))
    return [{"word": w, "score": score_word(w)} for w in matches[:20]]


@app.post("/api/upload-screenshot")
async def api_upload_screenshot(file: UploadFile = File(...)):
    """Parse a Wordle screenshot and return extracted guesses."""
    from imgparse import parse_screenshot

    contents = await file.read()
    guesses = parse_screenshot(contents)
    return {"guesses": guesses}


@app.post("/api/analyze-game")
def api_analyze_game(req: SolveRequest):
    """Analyze a completed Wordle game step-by-step.

    For each guess, shows:
    - Candidates remaining before and after
    - How many were eliminated
    - Greens/yellows accumulated
    - Top candidates that were available at that step
    - Group distribution showing how the guess partitioned candidates
    """
    total = np.array([0] * (26 * WORD_LENGTH * 3))
    all_words_list = list(words.keys())
    n_words = len(word_freq_rank)

    steps = []
    prev_candidates = all_words_list  # start with full dictionary

    for step_idx, g in enumerate(req.guesses):
        guess_word = g.word.lower()
        guess_result = g.result.lower()
        candidates_before = len(prev_candidates)

        # Apply this guess's constraints
        total, matches = get_words(total, guess_word, guess_result)

        # Find the best matching group
        if not matches:
            steps.append({
                "guess": guess_word,
                "result": guess_result,
                "step": step_idx + 1,
                "candidates_before": candidates_before,
                "candidates_after": 0,
                "eliminated": candidates_before,
                "elimination_pct": 100.0,
                "greens": get_greens(total),
                "yellows": get_yellows(total),
                "top_remaining": [],
                "group_distribution": [],
                "letter_analysis": [],
            })
            prev_candidates = []
            continue

        best_key = sorted(matches.keys(), key=lambda k: (k[0], k[1], k[2]))[-1]
        candidates = matches[best_key]
        candidates_after = len(candidates)
        eliminated = candidates_before - candidates_after

        # Compute group distribution: how did this guess partition the space?
        # For each possible result pattern, how many words would match?
        pattern_groups = defaultdict(list)
        for w in prev_candidates:
            if w in words:  # only valid words
                pattern = wordle_rank(guess_word, w)
                pattern_groups[pattern].append(w)

        # Sort groups by size descending, show top groups
        group_dist = []
        for pattern, group_words in sorted(pattern_groups.items(), key=lambda x: -len(x[1])):
            is_actual = (pattern == guess_result)
            group_dist.append({
                "pattern": pattern,
                "count": len(group_words),
                "is_actual": is_actual,
                "sample_words": sorted(group_words, key=lambda x: word_freq_rank.get(x, n_words))[:5],
            })

        # Analyze what each color in this guess contributed
        letter_analysis = []
        for i, (letter, color) in enumerate(zip(guess_word, guess_result)):
            if color == "g":
                info = f"'{letter}' is at position {i+1}"
            elif color == "y":
                info = f"'{letter}' is in the word but not at position {i+1}"
            else:
                # Check if the letter appears elsewhere as green/yellow
                other_occurrences = sum(1 for j, c in enumerate(guess_result) if j != i and guess_word[j] == letter and c in ("g", "y"))
                if other_occurrences > 0:
                    info = f"no additional '{letter}' beyond the one(s) found"
                else:
                    info = f"'{letter}' is not in the word"
            letter_analysis.append({
                "letter": letter,
                "position": i + 1,
                "color": color,
                "info": info,
            })

        # Top remaining candidates with elimination scores
        top_remaining = []
        elims = compute_eliminations(candidates) if len(candidates) <= 200 else {}
        for w in candidates[:10]:
            top_remaining.append({
                "word": w,
                "freq": word_freq.get(w, 0),
                "eliminations": elims.get(w, 0),
            })

        steps.append({
            "guess": guess_word,
            "result": guess_result,
            "step": step_idx + 1,
            "candidates_before": candidates_before,
            "candidates_after": candidates_after,
            "eliminated": eliminated,
            "elimination_pct": round(eliminated / candidates_before * 100, 1) if candidates_before > 0 else 0,
            "greens": get_greens(total),
            "yellows": get_yellows(total),
            "top_remaining": top_remaining,
            "group_distribution": group_dist[:20],  # top 20 groups
            "total_groups": len(pattern_groups),
            "letter_analysis": letter_analysis,
        })

        prev_candidates = candidates

    return {
        "steps": steps,
        "total_words": len(all_words_list),
        "solved": len(steps) > 0 and steps[-1]["candidates_after"] == 1,
        "answer": prev_candidates[0] if len(prev_candidates) == 1 else None,
    }


# Serve frontend static files in production
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))
