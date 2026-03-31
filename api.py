"""FastAPI backend wrapping wordle_ml solver logic."""

from collections import Counter, defaultdict
from math import sqrt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
letter_freq = [x[0] for x in c.most_common()]


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
    matches = defaultdict(list)
    for word, check in words.items():
        green = int(check[0:YELLOW_START].dot(total[0:YELLOW_START]))
        yellow = int(check[YELLOW_START:RED_START].dot(total[YELLOW_START:RED_START]))
        red = int(check[RED_START:].dot(total[RED_START:]))
        matches[(green, yellow, red)].append(word)

    for k, v in matches.items():
        v.sort(key=lambda x: word_freq_list.index(x) if x in word_freq_list else len(word_freq_list))

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


@app.post("/api/solve")
def api_solve(req: SolveRequest):
    """Given a list of guesses with results, return remaining candidates with scores."""
    total = np.array([0] * (26 * WORD_LENGTH * 3))

    all_matches = {}
    for g in req.guesses:
        total, matches = get_words(total, g.word.lower(), g.result.lower())
        all_matches = matches

    # Find the best matching group (highest green+yellow score)
    if not all_matches:
        return {"candidates": [], "greens": ".....", "yellows": "", "total_remaining": 0}

    best_key = sorted(all_matches.keys(), key=lambda k: sqrt(k[0]**2 + k[1]**2))[-1]
    candidates = all_matches[best_key]

    # Build candidate list with probability-like scores
    total_words = len(candidates)
    result_candidates = []
    for i, w in enumerate(candidates):
        freq = word_freq.get(w, 0)
        result_candidates.append({
            "word": w,
            "rank": i + 1,
            "freq": freq,
            "score": score_word(w),
            "match_key": list(best_key),
        })

    # Also return secondary groups for context
    groups = []
    for key in sorted(all_matches.keys(), key=lambda k: sqrt(k[0]**2 + k[1]**2), reverse=True):
        groups.append({
            "green": key[0],
            "yellow": key[1],
            "red": key[2],
            "count": len(all_matches[key]),
            "top_words": all_matches[key][:10],
        })

    return {
        "candidates": result_candidates[:200],
        "greens": get_greens(total),
        "yellows": get_yellows(total),
        "total_remaining": total_words,
        "groups": groups[:20],
    }


@app.get("/api/suggest/{word}")
def api_suggest(word: str):
    """Suggest words matching a partial pattern (for autocomplete)."""
    word = word.lower()
    matches = [w for w in words if w.startswith(word)]
    matches.sort(key=lambda x: word_freq_list.index(x) if x in word_freq_list else len(word_freq_list))
    return [{"word": w, "score": score_word(w)} for w in matches[:20]]
