import re
from collections import defaultdict, Counter
import sys
from itertools import combinations

length = 5
if sys.argv[1:]:
    length = int(sys.argv[1])


c = Counter()
words = []
positions = defaultdict(Counter)
with open("words_alpha.txt") as W:
    for line in W:
        w = line.strip()

        if len(w) != length or w != w.lower() or length - len(set(w)) != 0:
            continue

        c.update(w.lower())
        words.append(w)

        for i, l in enumerate(w):
            positions[i].update(l)

frequency = [x[0] for x in c.most_common()]
print(frequency)
for k, p in positions.items():
    print(k, p.most_common(10))
print(len(words))


def score_word(w):
    t = 0
    for l in set(w):
        t += frequency.index(l)
    return t


# words.sort(key=lambda x: score_word(x))

# all_words = set()
# for i, a in enumerate(words):
#     total = set(a)
#     for j, b in enumerate(
#         [w for w in words[i + 1 :] if len(total.intersection(set(w))) == 0]
#     ):
#         total = set(a + b)
#         for k, c in enumerate(
#             [w for w in words[j + 1 :] if len(total.intersection(set(w))) == 0]
#         ):
#             total = set(a + b + c)
#             for l, d in enumerate(
#                 [w for w in words[k + 1 :] if len(total.intersection(set(w))) == 0]
#             ):
#                 total = set(a + b + c + d)
#                 if tuple(total) not in all_words:
#                     print(a, b, c, d)
#                     all_words.add(tuple(total))
#                 for m, e in enumerate(
#                     [w for w in words[l + 1 :] if len(total.intersection(set(w))) == 0]
#                 ):
#                     print(a, b, c, d, e)


# sys.exit()

# for checks in [5, 4, 3]:
#     answers = {0: []}
#     for i, item in enumerate(combinations(words, checks)):
#         score = len(set("".join(item)))
#         if score > max(answers.keys()):
#             answers = {score: [item]}
#         elif score == max(answers.keys()):
#             answers[score].append(item)

#         if i % 10000000 == 0:
#             print(checks, i, score, item, list(answers.values())[-1][-3:-1])
#     else:
#         print(checks, i, answers)


# sys.exit()

while True:
    data = input("> ")
    opts = data.split(" ")
    guess = opts[0]

    include = []
    if len(opts) >= 2:
        include = opts[1]

    exclude = []
    if len(opts) >= 3:
        exclude = set(opts[2]) - set(guess)

    r = re.compile(guess)
    output = {}
    for w in words:
        if r.match(w):
            if not len(set(w).intersection(set(include))) == len(set(include)):
                continue

            if set(w).intersection(set(exclude)):
                continue

            t = 0
            for l in set(w):
                t += frequency.index(l)
            else:
                t += 25 * (5 - len(set(w)))
            # print(w, t)
            output[w] = t

    print(len(output), "words")

    print(
        " ".join(
            [f"{x[0]} {x[1]}" for x in sorted(output.items(), key=lambda x: x[1])[0:75]]
        )
    )
