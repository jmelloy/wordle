import random
from collections import defaultdict, Counter
import sys
from itertools import combinations

length = 5
if sys.argv[1:]:
    length = int(sys.argv[1])


c = Counter()
words = defaultdict(list)
positions = defaultdict(Counter)

with open("/usr/share/dict/words") as F:
    deny = {w.strip() for w in F.readlines()}

with open("words_alpha.txt") as W:
    for line in W:
        w = line.strip()

        if (
            len(w) != length
            or w != w.lower()
            or length - len(set(w)) > 1
            or w not in deny
        ):
            continue

        c.update(w.lower())
        words["".join(sorted(set(w)))].append(w)

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


all_words = {}
for a in words:
    print(a)
    total = set("".join(a))
    for b in [
        w
        for w in sorted(words, key=lambda x: score_word(x))
        if len(total.intersection(set(w))) < 2
    ]:
        total = set("".join(a) + "".join(b))
        for c in [
            w
            for w in sorted(words, key=lambda x: score_word(x))
            if len(total.intersection(set(w))) < 2
        ]:
            total = set("".join(a) + "".join(b) + "".join(c))
            for d in [
                w
                for w in sorted(words, key=lambda x: score_word(x))
                if len(total.intersection(set(w))) < 2
            ]:
                total = set("".join(a) + "".join(b) + "".join(c) + "".join(d))

                for e in [
                    w
                    for w in sorted(words, key=lambda x: score_word(x))
                    if len(total.intersection(set(w))) < 2
                ]:
                    all_words[len(set(a + b + c + d + e))] = [
                        random.choice(words[a]),
                        random.choice(words[b]),
                        random.choice(words[c]),
                        random.choice(words[d]),
                        random.choice(words[e]),
                    ]
            print(all_words)
