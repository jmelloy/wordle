import re, string
import random
import time

minlen = 3

subs = [
    # ('for', '4'),
    # ('four', '4'),
    # ('to', '2'),
    ("ate", "8"),
    # ('ten', '10'),
    # ('g', '6'),
    ("l", "1"),
    ("o", "0"),
    ("s", "5"),
    ("t", "7"),
]

lengths = {}

reHexWord = re.compile("^([a-f0-9]+)$")
fWords = open("words_alpha.txt", "r")
for w in fWords:
    w = w.strip()
    for old, new in subs:
        w = w.replace(old, new)
    if len(w) not in lengths:
        lengths[len(w)] = []

    match = reHexWord.match(w)
    if match:
        lengths[len(w)].append(w)

print({k: len(v) for k, v in lengths.items()})

while True:
    a = []
    for i in [8, 4, 4, 4, 12]:
        if random.randint(1, 10) > 5:
            a.append(random.choice(lengths[i]))
        else:
            a.append(random.choice(lengths[i / 2]) + random.choice(lengths[i / 2]))

    print("-".join(a).upper())
    time.sleep(1)
