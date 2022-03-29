import random
import sys

length = 5
words = []
with open("words_alpha.txt") as W:
    for line in W:
        w = line.strip()
        if len(w) != length or w != w.lower():
            continue
        words.append(w)

if sys.argv[1:]:
    word = sys.argv[1]
else:
    word = random.choice(word)

while word:
    print("Got new word")
    guess = ""
    include = set()
    exclude = set()
    tries = 0
    while guess != word:
        guess = input("guess? ")
        exclude.update(set(guess) - set(word))
        include.update(set(guess).intersection(set(word)))

        guesses = []
        for i, l in enumerate(guess):
            if word[i] != l:
                guesses.append(".")
            else:
                guesses.append(l)
        # print(guesses, include, exclude)
        print("".join(guesses), "".join(include - set(guesses)), "".join(exclude))

        tries += 1
    print(f"Got the word! {word} in {tries} tries")

    word = random.choice(word)
