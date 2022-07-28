from audioop import reverse
from collections import defaultdict, Counter
import enum
import sys
import numpy as np
from math import sqrt
import json
import os

c = Counter()

word_length = 5
if sys.argv[1:]:
    word_length = int(sys.argv[1])

alpha = "abcdefghijklmnopqrstuvwxyz"
red_start = word_length * 2 * 26
yellow_start = word_length * 26


def word_vec(word):
    num_list = (
        [0] * (26 * word_length) + [0] * (26 * word_length) + [1] * 26 * word_length
    )

    for i, l in enumerate(word):
        pos = i * 26 + alpha.index(l)
        num_list[pos] = 1
        for j in range(word_length):
            if j != i and word[j] != l:
                num_list[yellow_start + j * 26 + alpha.index(l)] = 1
    for x in set(word):
        count = word.count(x)
        for j in range(count):
            num_list[red_start + j * 26 + alpha.index(x)] = 0
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


words = {}
word_freq = {}
scores = {}

word_eliminations = defaultdict(set)
with open("unigram_freq.csv") as W:
    header = W.readline()
    for line in W:
        word, count = line.strip().split(",")

        if len(word) != word_length or word != word.lower():
            continue
        word_freq[word] = count

with open("twl06.txt") as W:
    header = W.readline()
    for line in W:
        word = line.strip()

        if len(word) != word_length or word != word.lower():
            continue

        words[word] = word_vec(word)

        c.update(word)
        if word not in word_freq:
            word_freq[word] = 1000000


word_freq = list(word_freq.keys())

letter_freq = [x[0] for x in c.most_common()]


def create_eliminations(word_list=words):
    word_eliminations = {}
    for word in word_list:
        l = list(word)
        for w in word_eliminations:
            wl = list(w)
            # print(word, w, l, wl, (set(l) & set(wl)) - {'.'})
            if set(l) & set(wl):
                # print(word, w, l, wl, (set(l) & set(wl)) - {'.'})
                word_eliminations[w].append(word)
        word_eliminations[word] = [word]
    return word_eliminations


# word_eliminations = create_eliminations()


def create_scores():
    if os.path.exists("words.json"):
        with open("words.json") as FILE:
            return json.load(FILE)

    scores = {}
    for word in words:
        for check in words:
            rank = wordle_rank(word, check)
            if word in scores:
                if rank in scores[word]:
                    scores[word][rank].append(check)
                else:
                    scores[word][rank] = [check]
            else:
                scores[word] = {rank: [check]}

    with open("words.json", "w") as FILE:
        json.dump(scores, FILE)

    return scores


def check_word(word, guess, word_list=None):
    if not word_list:
        word_list = set(scores[word][guess])
    else:
        word_list = set(scores[word][guess]) & set(word_list)
    # print(word_list)
    checks = []
    for word in word_list:
        checks.append(
            (
                word,
                [
                    word_list & set(v)
                    for k, v in scores[word].items()
                    if word_list & set(v)
                ],
            )
        )
    return sorted(checks, key=lambda x: len(x[1]), reverse=True)


def play():
    while True:
        word_lists = {}
        totals = {}
        print(sorted(scores, key=lambda x: len(scores[x]))[-1])

        while True:
            data = input("> ")
            if data == "qq":
                break
            opts = data.lower().split(" ")
            guess = opts[0]
            results = opts[1:]
            for quad, result in enumerate(results):
                total = totals.get(quad, [0] * (26 * 3 * word_length))
                guess_array = get_word_vec_guess(guess, result)
                total = np.logical_or(guess_array, total)
                print_compact_total(total)
                if result == "ggggg":
                    continue
                word_list = word_lists.get(quad, scores[guess][result])
                checks = check_word(guess, result, word_list)
                if not checks:
                    print("no words")
                    continue
                val = len(checks[0][1])
                word_lists[quad] = set(word_list) & set(scores[guess][result])
                totals[quad] = total
                for k, v in sorted(
                    filter(lambda x: len(x[1]) == val, checks),
                    key=lambda x: word_freq.index(x[0]),
                ):
                    print(k, len(v))
                print(
                    len(word_lists[quad]),
                    sorted(word_lists[quad], key=lambda x: word_freq.index(x))[0:10],
                )


def score(w):
    t = 0
    for l in w:
        t += letter_freq.index(l)
    return t


def get_word_vec_guess(guess, result):
    num_list = [0] * (26 * (word_length * 3))
    for i, l in enumerate(guess):
        base = i
        if result[i].lower() == "r":
            base = 2 * word_length
            mod = guess.count(l) - 1
            base += mod
        elif result[i].lower() == "y":
            base = word_length + i
        pos = base * 26 + alpha.index(l)
        num_list[pos] = 1
    return np.array(num_list)


def get_words(total, guess, result):
    guess_array = get_word_vec_guess(guess, result)

    total = np.logical_or(guess_array, total)
    matches = defaultdict(list)
    for word, check in words.items():
        green_guesses = check[0:yellow_start].dot(total[0:yellow_start])
        yellow_guesses = check[yellow_start:red_start].dot(
            total[yellow_start:red_start]
        )

        red_guesses = check[red_start:].dot(total[red_start:])

        matches[
            (
                green_guesses,
                yellow_guesses,
                red_guesses,
            )
        ].append(word)

    for k, v in matches.items():
        v.sort(key=lambda x: word_freq.index(x))

    return total, matches


def print_total(total):
    for i in range(0, len(total), 26):
        for j in range(26):
            if total[i + j]:
                print(alpha[j], end="")
            else:
                print(".", end="")
        print()


def print_compact_total(total):
    word = []
    for i in range(len(total) // 26):
        if i and i % word_length == 0:
            if i > word_length:
                word = set(word)
            print("".join(word), end=" ")
            word = []

        for j in range(26):
            if total[i * 26 + j]:
                word.append(alpha[j])
        else:
            if i < word_length and len(word) != i + 1:
                word.append(".")
    print("".join(word))


# arose grrrg gygrg rrrgr rrryy
# adore grrrg ggggg ryrrr rrrry
# midst rrrry ggggg ggggg rgryr
# agate ggggg ggggg ggggg rrrry

# > arose ygrrr ygrrr yryrr rrrgy
# > track yggrr rggrr rryrr yrrrr
# > guest rrrrg rrrrr rrrrr ggggg
# > draft ggggg gggrr rryrr ggggg
# > drama ggggg gggrr rryrr ggggg
# > drawn ggggg gggrg rryry ggggg
# > inbox ggggg yyrrr ryyyr ggggg
# > drain ggggg ggggg rryry ggggg


def magnitude(best_match):
    return sqrt(best_match[0] * best_match[0] + best_match[1] * best_match[1])


def eliminations(word_list, yellow=None, greens=None):
    if not yellow:
        yellow = set()
    if not greens:
        greens = set()

    elims = {w: set(word_eliminations[w]) & set(word_list) for w in word_list}
    for word, vals in elims.items():
        elims[word] = len(
            {v for v in vals if (set(word) & set(v)) - set(yellow) - set(greens)}
        )

    return sorted(elims.items(), key=lambda k: k[1], reverse=True)[0:10]


def get_greens(total):
    word = ["."] * word_length
    for i in range(0, yellow_start):
        if total[i] == 1:
            word[i // 26] = alpha[i % 26]
    return "".join(word)


def get_yellows(total):
    word = set()
    for i in range(yellow_start, red_start):
        if total[i] == 1:
            word.add(alpha[i % 26])
    return "".join(word)


if __name__ == "__main__":
    scores = create_scores()
    play()

    # arose grrrg gygrg rrrgr rrryy
    totals = []

    while True:
        data = input("> ")
        opts = data.split(" ")
        guess = opts[0]

        results = opts[1:]

        for quad, result in enumerate(results):
            total = [0] * (26 * 3 * word_length)
            if quad == len(totals):
                totals.append(total)

            total = totals[quad]
            total, matches = get_words(total, guess, result)
            totals[quad] = total

            print_compact_total(total)
            best_match = sorted(matches.keys())[-1]
            print(
                matches[best_match][0:10],
                best_match,
                len(matches[best_match]),
            )
            print(
                eliminations(matches[best_match], get_yellows(total)), get_greens(total)
            )
