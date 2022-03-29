from collections import defaultdict, Counter
import sys
import numpy as np
from math import sqrt

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


words = {}

with open("unigram_freq.csv") as W:
    header = W.readline()
    for line in W:
        word, count = line.strip().split(",")

        if len(word) != word_length or word != word.lower():
            continue

        words[word] = word_vec(word)
        c.update(word.lower())

frequency = [x[0] for x in c.most_common()]


def score(w):
    t = 0
    for l in w:
        t += frequency.index(l)
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


if __name__ == "__main__":

    # arose grrrg gygrg rrrgr rrryy
    totals = []

    while True:
        data = input("> ")
        opts = data.split(" ")
        guess = opts[0]

        results = opts[1:]
        scores = []
        for quad, result in enumerate(results):
            if quad == len(totals):
                total = [0] * (26 * 3 * word_length)
                totals.append(total)

            total = totals[quad]
            total, matches = get_words(total, guess, result)
            totals[quad] = total

            print_compact_total(total)
            best_match = sorted(matches.keys())[-1]
            print(
                matches[best_match][0:10],
                best_match,
                magnitude(best_match=best_match),
            )
