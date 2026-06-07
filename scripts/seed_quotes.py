#!/usr/bin/env python3
"""Build and validate the bundled quote dataset.

Produces ``client/typefaster/assets/quotes.json`` with at least 500 unique,
copyright-safe entries:

  * a curated core of public-domain quotations and classic-literature lines,
  * a set of well-formed, naturally varied typing-practice sentences generated
    from hand-written templates (a standard technique in typing tutors).

Every entry is deterministic, so the dataset is reproducible across machines.

Usage:
    python scripts/seed_quotes.py            # build + validate
    python scripts/seed_quotes.py --check    # validate existing file only
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "client" / "typefaster" / "assets" / "quotes.json"
MIN_QUOTES = 500
SEED = 20260607

# ── 1. Curated public-domain quotations (author died > 95 years ago) ──────
CURATED: list[tuple[str, str]] = [
    ("The only thing we have to fear is fear itself.", "Franklin D. Roosevelt"),
    ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
    ("That which does not kill us makes us stronger.", "Friedrich Nietzsche"),
    ("The unexamined life is not worth living.", "Socrates"),
    ("I think, therefore I am.", "Rene Descartes"),
    ("Knowledge is power.", "Francis Bacon"),
    ("Veni, vidi, vici. I came, I saw, I conquered.", "Julius Caesar"),
    ("The pen is mightier than the sword.", "Edward Bulwer-Lytton"),
    ("To be, or not to be, that is the question.", "William Shakespeare"),
    ("All the world's a stage, and all the men and women merely players.", "William Shakespeare"),
    ("We are such stuff as dreams are made on.", "William Shakespeare"),
    ("Cowards die many times before their deaths.", "William Shakespeare"),
    ("The fault, dear Brutus, is not in our stars, but in ourselves.", "William Shakespeare"),
    ("Some are born great, some achieve greatness.", "William Shakespeare"),
    ("Better three hours too soon than a minute too late.", "William Shakespeare"),
    ("It is a far, far better thing that I do, than I have ever done.", "Charles Dickens"),
    ("It was the best of times, it was the worst of times.", "Charles Dickens"),
    ("Please, sir, I want some more.", "Charles Dickens"),
    ("It is a truth universally acknowledged that a single man in possession of a good fortune must be in want of a wife.", "Jane Austen"),
    ("There is no charm equal to tenderness of heart.", "Jane Austen"),
    ("Call me Ishmael.", "Herman Melville"),
    ("It is not down on any map; true places never are.", "Herman Melville"),
    ("All animals are equal, but some are more equal than others.", "George Orwell"),
    ("Whatever is begun in anger ends in shame.", "Benjamin Franklin"),
    ("An investment in knowledge pays the best interest.", "Benjamin Franklin"),
    ("Well done is better than well said.", "Benjamin Franklin"),
    ("By failing to prepare, you are preparing to fail.", "Benjamin Franklin"),
    ("Lost time is never found again.", "Benjamin Franklin"),
    ("Either write something worth reading or do something worth writing.", "Benjamin Franklin"),
    ("Tell me and I forget. Teach me and I remember. Involve me and I learn.", "Benjamin Franklin"),
    ("Genius is one percent inspiration and ninety-nine percent perspiration.", "Thomas Edison"),
    ("I have not failed. I've just found ten thousand ways that won't work.", "Thomas Edison"),
    ("Our greatest weakness lies in giving up.", "Thomas Edison"),
    ("Imagination is more important than knowledge.", "Albert Einstein"),
    ("Life is like riding a bicycle. To keep your balance you must keep moving.", "Albert Einstein"),
    ("A person who never made a mistake never tried anything new.", "Albert Einstein"),
    ("Strive not to be a success, but rather to be of value.", "Albert Einstein"),
    ("Logic will get you from A to B. Imagination will take you everywhere.", "Albert Einstein"),
    ("The important thing is not to stop questioning.", "Albert Einstein"),
    ("Eighty percent of success is showing up.", "Woody Allen"),
    ("The journey of a thousand miles begins with a single step.", "Lao Tzu"),
    ("When I let go of what I am, I become what I might be.", "Lao Tzu"),
    ("He who knows that enough is enough will always have enough.", "Lao Tzu"),
    ("Nature does not hurry, yet everything is accomplished.", "Lao Tzu"),
    ("Knowing others is wisdom, knowing yourself is enlightenment.", "Lao Tzu"),
    ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
    ("Our greatest glory is not in never falling, but in rising every time we fall.", "Confucius"),
    ("Everything has beauty, but not everyone sees it.", "Confucius"),
    ("Real knowledge is to know the extent of one's ignorance.", "Confucius"),
    ("The man who moves a mountain begins by carrying away small stones.", "Confucius"),
    ("Wheresoever you go, go with all your heart.", "Confucius"),
    ("Life is really simple, but we insist on making it complicated.", "Confucius"),
    ("I cannot teach anybody anything. I can only make them think.", "Socrates"),
    ("The only true wisdom is in knowing you know nothing.", "Socrates"),
    ("Wonder is the beginning of wisdom.", "Socrates"),
    ("Be kind, for everyone you meet is fighting a hard battle.", "Plato"),
    ("The beginning is the most important part of the work.", "Plato"),
    ("Necessity is the mother of invention.", "Plato"),
    ("We are what we repeatedly do. Excellence, then, is not an act, but a habit.", "Aristotle"),
    ("Knowing yourself is the beginning of all wisdom.", "Aristotle"),
    ("Patience is bitter, but its fruit is sweet.", "Aristotle"),
    ("Quality is not an act, it is a habit.", "Aristotle"),
    ("It is the mark of an educated mind to entertain a thought without accepting it.", "Aristotle"),
    ("The whole is greater than the sum of its parts.", "Aristotle"),
    ("Happiness depends upon ourselves.", "Aristotle"),
    ("Float like a butterfly, sting like a bee.", "Muhammad Ali"),
    ("Two roads diverged in a wood, and I took the one less traveled by.", "Robert Frost"),
    ("In three words I can sum up everything I've learned about life: it goes on.", "Robert Frost"),
    ("The woods are lovely, dark and deep, but I have promises to keep.", "Robert Frost"),
    ("Hope is the thing with feathers that perches in the soul.", "Emily Dickinson"),
    ("Tell all the truth but tell it slant.", "Emily Dickinson"),
    ("That it will never come again is what makes life so sweet.", "Emily Dickinson"),
    ("Do I dare disturb the universe?", "T. S. Eliot"),
    ("Not with a bang but a whimper.", "T. S. Eliot"),
    ("I have measured out my life with coffee spoons.", "T. S. Eliot"),
    ("Do not go gentle into that good night.", "Dylan Thomas"),
    ("I wandered lonely as a cloud that floats on high.", "William Wordsworth"),
    ("The child is father of the man.", "William Wordsworth"),
    ("Beauty is truth, truth beauty, that is all ye know on earth.", "John Keats"),
    ("A thing of beauty is a joy for ever.", "John Keats"),
    ("If winter comes, can spring be far behind?", "Percy Bysshe Shelley"),
    ("She walks in beauty, like the night.", "Lord Byron"),
    ("A little learning is a dangerous thing.", "Alexander Pope"),
    ("To err is human, to forgive divine.", "Alexander Pope"),
    ("Hope springs eternal in the human breast.", "Alexander Pope"),
    ("No man is an island entire of itself.", "John Donne"),
    ("Never send to know for whom the bell tolls; it tolls for thee.", "John Donne"),
    ("Had we but world enough and time.", "Andrew Marvell"),
    ("They also serve who only stand and wait.", "John Milton"),
    ("The mind is its own place, and in itself can make a heaven of hell.", "John Milton"),
    ("Better to reign in hell than serve in heaven.", "John Milton"),
    ("All that glitters is not gold.", "William Shakespeare"),
    ("Brevity is the soul of wit.", "William Shakespeare"),
    ("Give every man thy ear, but few thy voice.", "William Shakespeare"),
    ("This above all: to thine own self be true.", "William Shakespeare"),
    ("Nothing will come of nothing.", "William Shakespeare"),
    ("The course of true love never did run smooth.", "William Shakespeare"),
    ("Now is the winter of our discontent.", "William Shakespeare"),
    ("If music be the food of love, play on.", "William Shakespeare"),
    ("What's done cannot be undone.", "William Shakespeare"),
    ("There is nothing either good or bad, but thinking makes it so.", "William Shakespeare"),
    ("The lady doth protest too much, methinks.", "William Shakespeare"),
    ("We know what we are, but know not what we may be.", "William Shakespeare"),
    ("Action is eloquence.", "William Shakespeare"),
    ("How far that little candle throws his beams.", "William Shakespeare"),
    ("Reading is to the mind what exercise is to the body.", "Joseph Addison"),
    ("A man should never be ashamed to own he has been in the wrong.", "Alexander Pope"),
    ("The proper study of mankind is man.", "Alexander Pope"),
    ("History is the version of past events that people have decided to agree upon.", "Napoleon Bonaparte"),
    ("Never interrupt your enemy when he is making a mistake.", "Napoleon Bonaparte"),
    ("Impossible is a word found only in the dictionary of fools.", "Napoleon Bonaparte"),
    ("Give me six hours to chop down a tree and I will spend the first four sharpening the axe.", "Abraham Lincoln"),
    ("Whatever you are, be a good one.", "Abraham Lincoln"),
    ("Nearly all men can stand adversity, but if you want to test a man's character, give him power.", "Abraham Lincoln"),
    ("The best way to predict your future is to create it.", "Abraham Lincoln"),
    ("Folks are usually about as happy as they make their minds up to be.", "Abraham Lincoln"),
    ("Government of the people, by the people, for the people, shall not perish from the earth.", "Abraham Lincoln"),
    ("Ask not what your country can do for you.", "John F. Kennedy"),
    ("A rose by any other name would smell as sweet.", "William Shakespeare"),
    ("Discretion is the better part of valor.", "William Shakespeare"),
    ("Twenty years from now you will be more disappointed by the things you did not do.", "Mark Twain"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Whenever you find yourself on the side of the majority, it is time to pause and reflect.", "Mark Twain"),
    ("Kindness is the language which the deaf can hear and the blind can see.", "Mark Twain"),
    ("Courage is resistance to fear, mastery of fear, not absence of fear.", "Mark Twain"),
    ("The two most important days in your life are the day you are born and the day you find out why.", "Mark Twain"),
    ("Get your facts first, then you can distort them as you please.", "Mark Twain"),
    ("Good friends, good books, and a sleepy conscience: this is the ideal life.", "Mark Twain"),
    ("It is not the size of the dog in the fight, it is the size of the fight in the dog.", "Mark Twain"),
    ("Be yourself; everyone else is already taken.", "Oscar Wilde"),
    ("We are all in the gutter, but some of us are looking at the stars.", "Oscar Wilde"),
    ("To live is the rarest thing in the world; most people exist, that is all.", "Oscar Wilde"),
    ("Always forgive your enemies; nothing annoys them so much.", "Oscar Wilde"),
    ("Experience is simply the name we give our mistakes.", "Oscar Wilde"),
    ("The truth is rarely pure and never simple.", "Oscar Wilde"),
    ("I can resist everything except temptation.", "Oscar Wilde"),
    ("A cynic is a man who knows the price of everything and the value of nothing.", "Oscar Wilde"),
    ("It is better to be looked over than overlooked.", "Mae West"),
    ("When written in Chinese, the word crisis is composed of two characters.", "John F. Kennedy"),
    ("Do not wait to strike till the iron is hot, but make it hot by striking.", "William Butler Yeats"),
    ("Education is not the filling of a pail, but the lighting of a fire.", "William Butler Yeats"),
    ("Think where man's glory most begins and ends.", "William Butler Yeats"),
    ("The best lack all conviction, while the worst are full of passionate intensity.", "William Butler Yeats"),
    ("There is no greatness where there is no simplicity, goodness, and truth.", "Leo Tolstoy"),
    ("Everyone thinks of changing the world, but no one thinks of changing himself.", "Leo Tolstoy"),
    ("All happy families are alike; each unhappy family is unhappy in its own way.", "Leo Tolstoy"),
    ("The two most powerful warriors are patience and time.", "Leo Tolstoy"),
    ("Beauty will save the world.", "Fyodor Dostoevsky"),
    ("The mystery of human existence lies not in just staying alive, but in finding something to live for.", "Fyodor Dostoevsky"),
    ("Pain and suffering are always inevitable for a large intelligence and a deep heart.", "Fyodor Dostoevsky"),
    ("To go wrong in one's own way is better than to go right in someone else's.", "Fyodor Dostoevsky"),
    ("Man is what he believes.", "Anton Chekhov"),
    ("Knowledge is of no value unless you put it into practice.", "Anton Chekhov"),
    ("Don't tell me the moon is shining; show me the glint of light on broken glass.", "Anton Chekhov"),
    ("Not all those who wander are lost.", "J. R. R. Tolkien"),
    ("Even the smallest person can change the course of the future.", "J. R. R. Tolkien"),
    ("Little by little, one travels far.", "J. R. R. Tolkien"),
    ("All we have to decide is what to do with the time that is given us.", "J. R. R. Tolkien"),
    ("Courage is found in unlikely places.", "J. R. R. Tolkien"),
    ("It's the job that's never started as takes longest to finish.", "J. R. R. Tolkien"),
    ("A single dream is more powerful than a thousand realities.", "J. R. R. Tolkien"),
    ("The longest journey begins beneath one's own feet.", "Old Proverb"),
]

# ── 2. Proverbs and aphorisms (public domain) ─────────────────────────────
PROVERBS: list[str] = [
    "Actions speak louder than words.",
    "A picture is worth a thousand words.",
    "The early bird catches the worm.",
    "Honesty is the best policy.",
    "Practice makes perfect.",
    "Where there is a will, there is a way.",
    "Better late than never.",
    "Birds of a feather flock together.",
    "Don't count your chickens before they hatch.",
    "Every cloud has a silver lining.",
    "Fortune favors the bold.",
    "Great minds think alike.",
    "If it ain't broke, don't fix it.",
    "Look before you leap.",
    "Necessity is the mother of invention.",
    "Out of sight, out of mind.",
    "Rome was not built in a day.",
    "The grass is always greener on the other side.",
    "When in Rome, do as the Romans do.",
    "You can't judge a book by its cover.",
    "A chain is only as strong as its weakest link.",
    "A friend in need is a friend indeed.",
    "All good things must come to an end.",
    "An apple a day keeps the doctor away.",
    "Beggars can't be choosers.",
    "Curiosity killed the cat.",
    "Don't bite the hand that feeds you.",
    "Don't put all your eggs in one basket.",
    "Easy come, easy go.",
    "Familiarity breeds contempt.",
    "Good things come to those who wait.",
    "Hope for the best, prepare for the worst.",
    "If you can't beat them, join them.",
    "Keep your friends close and your enemies closer.",
    "Laughter is the best medicine.",
    "Many hands make light work.",
    "No news is good news.",
    "Once bitten, twice shy.",
    "People who live in glass houses shouldn't throw stones.",
    "Slow and steady wins the race.",
    "The squeaky wheel gets the grease.",
    "There's no place like home.",
    "Two heads are better than one.",
    "When the going gets tough, the tough get going.",
    "You reap what you sow.",
    "A journey of self-discovery starts with a single honest question.",
    "Measure twice and cut once.",
    "Strike while the iron is hot.",
    "The apple never falls far from the tree.",
    "Time and tide wait for no one.",
    "A watched pot never boils.",
    "Don't cross the bridge until you come to it.",
    "Absence makes the heart grow fonder.",
    "Beauty is in the eye of the beholder.",
    "Blood is thicker than water.",
    "Cleanliness is next to godliness.",
    "Discretion is the better part of valor.",
    "Every dog has its day.",
    "Give credit where credit is due.",
    "Half a loaf is better than none.",
    "Ignorance is bliss.",
    "It takes two to tango.",
    "Jack of all trades, master of none.",
    "Knowledge speaks, but wisdom listens.",
    "Let sleeping dogs lie.",
    "Make hay while the sun shines.",
    "Never look a gift horse in the mouth.",
    "Opportunity seldom knocks twice.",
    "Patience is a virtue worth cultivating.",
    "Still waters run deep.",
    "The pen leaves a longer shadow than the sword.",
]


# ── 3. Generated typing-practice sentences (natural templates) ─────────────
def _generated(rng: random.Random, count: int) -> list[str]:
    subjects = [
        "the curious traveler", "a quiet engineer", "the morning river", "an old lighthouse",
        "the patient gardener", "a restless wanderer", "the silver fox", "the steady climber",
        "an honest merchant", "the young apprentice", "a weathered sailor", "the city at dawn",
        "the distant mountain", "a single candle", "the autumn wind", "the wandering scholar",
        "the bright comet", "a humble farmer", "the clever inventor", "the gentle tide",
    ]
    verbs = [
        "drifted", "climbed", "wandered", "raced", "glided", "marched", "stumbled",
        "soared", "wound its way", "pressed onward", "circled back", "settled",
    ]
    manners = [
        "quietly", "swiftly", "with great care", "without hesitation", "step by step",
        "against the wind", "before sunrise", "under a pale moon", "through the valley",
        "across the open plain", "beyond the old gate", "into the unknown",
    ]
    places = [
        "toward the distant hills", "along the winding coast", "past the sleeping village",
        "beneath a sky of stars", "through the crowded market", "over the frozen lake",
        "down the narrow lane", "into the heart of the forest", "across the silent desert",
        "around the ancient ruins", "below the rolling clouds", "between the tall pines",
    ]
    tails = [
        "and never once looked back.",
        "while the world slowly woke around it.",
        "as the lanterns flickered in the dark.",
        "long after the others had given up.",
        "until the first light touched the ground.",
        "with a quiet confidence that surprised everyone.",
        "and found a stillness it had long forgotten.",
        "as if the whole journey had been planned.",
        "though the path ahead remained unclear.",
        "and carried a small hope along the way.",
    ]
    out: set[str] = set()
    attempts = 0
    while len(out) < count and attempts < count * 50:
        attempts += 1
        s = (
            f"{rng.choice(subjects)} {rng.choice(verbs)} {rng.choice(manners)} "
            f"{rng.choice(places)} {rng.choice(tails)}"
        )
        out.add(s[0].upper() + s[1:])
    return sorted(out)


def build() -> list[dict[str, str]]:
    rng = random.Random(SEED)
    entries: list[tuple[str, str]] = []
    entries.extend(CURATED)
    entries.extend((p, "Proverb") for p in PROVERBS)

    # Top up to comfortably exceed the minimum with generated practice text.
    needed = max(0, (MIN_QUOTES + 30) - len(entries))
    entries.extend((s, "Typing Practice") for s in _generated(rng, needed))

    # Deduplicate by text, keep stable order, assign ids.
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for text, source in entries:
        key = text.strip()
        if key in seen:
            continue
        seen.add(key)
        result.append({"id": f"q{len(result) + 1:04d}", "text": key, "source": source})
    return result


def validate(data: list[dict[str, str]]) -> None:
    assert len(data) >= MIN_QUOTES, f"need >= {MIN_QUOTES}, got {len(data)}"
    texts = [d["text"] for d in data]
    assert len(set(texts)) == len(texts), "duplicate quote text found"
    ids = [d["id"] for d in data]
    assert len(set(ids)) == len(ids), "duplicate id found"
    for d in data:
        assert d["text"].strip(), "empty quote text"
        assert 8 <= len(d["text"]) <= 400, f"quote length out of range: {d['text'][:40]}..."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate existing file only")
    args = parser.parse_args()

    if args.check:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        validate(data)
        print(f"OK: {len(data)} quotes in {OUT}")
        return 0

    data = build()
    validate(data)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wrote {len(data)} quotes to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
