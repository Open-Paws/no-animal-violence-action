#!/usr/bin/env python3
"""Self-contained scanner for language that normalizes violence toward animals.

All rules are embedded as Python data structures — no external dependencies.
Runs on any Python 3.6+ interpreter without third-party packages.

Usage (invoked by action.yml):
    python3 scan.py

Environment variables:
    INPUT_PATHS     Space-separated paths to scan (default: ".")
    INPUT_SEVERITY  Minimum severity that exits non-zero: error|warning|info (default: warning)

Output:
    GitHub Actions workflow command annotations on stdout:
        ::error file=PATH,line=N::"phrase" — reason. Consider: alt1, alt2
    Summary line on stdout.
    Exits 1 when findings at or above INPUT_SEVERITY are found.
"""

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Rule definitions
# Each rule: name, patterns (list of compiled re), phrase (display string),
# alternatives (list of str), reason (non-empty str), severity (str),
# word_boundary (bool used to build patterns).
# ---------------------------------------------------------------------------

def _p(terms, word_boundary=False):
    """Compile a list of term strings into a list of case-insensitive patterns."""
    compiled = []
    for term in terms:
        escaped = re.escape(term)
        if word_boundary:
            pattern = r"(?<![\w])" + escaped + r"(?![\w])"
        else:
            pattern = escaped
        compiled.append(re.compile(pattern, re.IGNORECASE))
    return compiled


def _r(regex):
    """Compile a raw regex string into a case-insensitive pattern."""
    return [re.compile(regex, re.IGNORECASE)]


RULES = [
    {
        "name": "kill-two-birds-with-one-stone",
        "patterns": _r(r"kill\s+two\s+birds\s+with\s+one\s+stone"),
        "phrase": "kill two birds with one stone",
        "alternatives": ["accomplish two things at once", "solve two problems with one action", "hit two targets with one shot"],
        "reason": "This phrase frames killing animals as a routine way to solve a problem. Plain alternatives like 'accomplish two things at once' carry the same meaning without invoking harm.",
        "severity": "error",
    },
    {
        "name": "beat-a-dead-horse",
        "patterns": _r(r"beat(ing)?\s+a\s+dead\s+horse"),
        "phrase": "beat a dead horse",
        "alternatives": ["belabor the point", "go over old ground", "repeat unnecessarily"],
        "reason": "This phrase uses an image of striking an animal's body as a metaphor for wasted effort. 'Belabor the point' is clearer and skips the imagery.",
        "severity": "error",
    },
    {
        "name": "skin-a-cat",
        "patterns": _r(r"(more\s+than\s+one|another|different|several)\s+way[s]?\s+to\s+skin\s+a\s+cat"),
        "phrase": "more than one way to skin a cat",
        "alternatives": ["more than one way to peel an orange", "multiple approaches available", "several ways to do this"],
        "reason": "Cat skinning as a metaphor for having options. 'Multiple approaches available' or 'more than one way to peel an orange' carries the same meaning.",
        "severity": "error",
    },
    {
        "name": "let-the-cat-out-of-the-bag",
        "patterns": _r(r"let\s+the\s+cat\s+out\s+of\s+the\s+bag"),
        "phrase": "let the cat out of the bag",
        "alternatives": ["reveal the secret", "disclose prematurely", "let it slip"],
        "reason": "Traced to fraudulent livestock markets and implies trapping animals. 'Reveal the secret' says the same thing more directly.",
        "severity": "info",
    },
    {
        "name": "open-a-can-of-worms",
        "patterns": _r(r"open(ing)?\s+a\s+can\s+of\s+worms"),
        "phrase": "open a can of worms",
        "alternatives": ["create a complicated situation", "uncover hidden problems", "open Pandora's box"],
        "reason": "References worms packaged as live bait to catch and kill fish. 'Open a difficult topic' or 'uncover hidden problems' is more precise.",
        "severity": "info",
    },
    {
        "name": "wild-goose-chase",
        "patterns": _r(r"wild\s+goose\s+chase"),
        "phrase": "wild goose chase",
        "alternatives": ["futile search", "pointless pursuit", "fool's errand"],
        "reason": "Casts pursuing a living bird as a pointless annoyance. 'Futile search' or 'fool's errand' says the same thing without the hunting framing.",
        "severity": "info",
    },
    {
        "name": "shooting-fish-in-a-barrel",
        "patterns": _r(r"(like\s+)?shoot(ing)?\s+fish\s+in\s+a\s+barrel"),
        "phrase": "shooting fish in a barrel",
        "alternatives": ["trivially easy", "a sure thing", "no challenge at all"],
        "reason": "Mass-killing imagery used to mean 'easy.' 'Trivially easy' or 'a sure thing' says the same thing without it.",
        "severity": "error",
    },
    {
        "name": "flog-a-dead-horse",
        "patterns": _r(r"flog(ging)?\s+a\s+dead\s+horse"),
        "phrase": "flog a dead horse",
        "alternatives": ["belabor the point", "waste effort on a settled matter", "repeat unnecessarily"],
        "reason": "Describes whipping an animal's corpse — the same image as 'beat a dead horse'. 'Belabor the point' is a direct replacement.",
        "severity": "error",
    },
    {
        "name": "bigger-fish-to-fry",
        "patterns": _r(r"(bigger|other)\s+fish\s+to\s+fry"),
        "phrase": "bigger fish to fry",
        "alternatives": ["more important matters to address", "bigger fish to free"],
        "reason": "Fish-as-food commodification for 'more important things.' 'More important matters' says the same thing.",
        "severity": "info",
    },
    {
        "name": "guinea-pig",
        "patterns": _r(r"guinea\s+pig"),
        "phrase": "guinea pig",
        "alternatives": ["test subject", "first to try", "early adopter"],
        "reason": "Refers to using guinea pigs as expendable test subjects in harmful experiments. 'Test subject' or 'early adopter' is more precise in technical contexts.",
        "severity": "warning",
    },
    {
        "name": "bring-home-the-bacon",
        "patterns": _r(r"(?:bring(?:ing|s)?|brought)\s+home\s+the\s+bacon"),
        "phrase": "bring home the bacon",
        "alternatives": ["bring home the results", "earn a living", "win the prize"],
        "reason": "Describes slaughtered pig flesh as the fruit of success. 'Bring home the results' or 'earn a living' carries the same meaning.",
        "severity": "error",
    },
    {
        "name": "take-the-bull-by-horns",
        "patterns": _r(r"tak(e|ing|es|en)\s+the\s+bull\s+by\s+the\s+horns|took\s+the\s+bull\s+by\s+the\s+horns"),
        "phrase": "take the bull by the horns",
        "alternatives": ["tackle the problem directly", "face it head-on", "confront the issue"],
        "reason": "Bullfighting/rodeo imagery. 'Tackle the problem directly' or 'face it head-on' is cleaner.",
        "severity": "warning",
    },
    {
        "name": "lambs-to-slaughter",
        "patterns": _r(r"(like\s+(a\s+)?)?lambs?\s+to\s+the\s+slaughter"),
        "phrase": "lambs to the slaughter",
        "alternatives": ["without resistance", "unknowingly walking into danger", "defenseless"],
        "reason": "Direct slaughter imagery. 'Without resistance' or 'unknowingly walking into danger' captures the same meaning.",
        "severity": "error",
    },
    {
        "name": "no-room-to-swing-a-cat",
        "patterns": _r(r"(no|not\s+enough)\s+room\s+to\s+swing\s+a\s+cat"),
        "phrase": "no room to swing a cat",
        "alternatives": ["extremely tight space", "very cramped"],
        "reason": "Violent animal imagery for 'cramped.' 'Extremely tight space' says it directly.",
        "severity": "warning",
    },
    {
        "name": "red-herring",
        "patterns": _r(r"red\s+herring"),
        "phrase": "red herring",
        "alternatives": ["distraction", "false lead", "misleading clue"],
        "reason": "Originates from dead, smoked fish reportedly used to train hunting dogs. 'Distraction' or 'false lead' communicates the idea directly.",
        "severity": "info",
    },
    {
        "name": "curiosity-killed-the-cat",
        "patterns": _r(r"curiosity\s+killed\s+the\s+cat"),
        "phrase": "curiosity killed the cat",
        "alternatives": ["curiosity backfired", "being nosy caused trouble", "curiosity led to trouble"],
        "reason": "A direct reference to killing a cat, used as a cautionary phrase. 'Curiosity backfired' or 'being nosy caused trouble' says the same thing.",
        "severity": "error",
    },
    {
        "name": "chicken-head-cut-off",
        "patterns": _r(r"(running\s+around\s+)?like\s+a\s+chicken\s+with\s+(its|their)\s+head\s+cut\s+off"),
        "phrase": "like a chicken with its head cut off",
        "alternatives": ["like your hair is on fire", "in a panic", "frantic and aimless"],
        "reason": "Graphic slaughter imagery used to describe panic. 'In a panic' or 'like your hair is on fire' captures the same thing.",
        "severity": "error",
    },
    {
        "name": "goose-is-cooked",
        "patterns": _r(r"(your|their|his|her|my|our)\s+goose\s+is\s+cooked"),
        "phrase": "your goose is cooked",
        "alternatives": ["you're in trouble", "you're done for", "you're dead in the water"],
        "reason": "Killing-and-cooking imagery used to mean someone is in trouble. 'You're in trouble' says it directly.",
        "severity": "error",
    },
    {
        "name": "throw-to-wolves",
        "patterns": _r(r"thr(ow|owing|own|ew)(\s+(someone|them|him|her|us|me))?\s+to\s+the\s+wolves"),
        "phrase": "throw someone to the wolves",
        "alternatives": ["abandon to criticism", "sacrifice someone", "leave exposed"],
        "reason": "Frames a person as prey. 'Abandon to criticism' or 'leave exposed' carries the same meaning without the imagery.",
        "severity": "error",
    },
    {
        "name": "hook-line-and-sinker",
        "patterns": _r(r"hook,?\s+line,?\s+and\s+sinker"),
        "phrase": "hook, line, and sinker",
        "alternatives": ["completely", "without question", "fell for it entirely"],
        "reason": "References the equipment used to hook and kill fish. 'Completely' or 'without question' conveys total buy-in without the fishing imagery.",
        "severity": "warning",
    },
    {
        "name": "clip-wings",
        "patterns": _r(r"clip(s|ped|ping)?\s+(someone's|their|his|her)?\s*wings"),
        "phrase": "clip someone's wings",
        "alternatives": ["restrict freedom", "limit options", "hold back"],
        "reason": "Wing-clipping is a real physical mutilation done to captive birds. 'Restrict freedom' or 'limit options' says the same thing directly.",
        "severity": "warning",
    },
    {
        "name": "straw-that-broke-camels-back",
        "patterns": _r(r"straw\s+that\s+broke\s+the\s+camel'?s\s+back|last\s+straw"),
        "phrase": "straw that broke the camel's back",
        "alternatives": ["tipping point", "breaking point", "final blow"],
        "reason": "Overloading a pack animal until its back breaks. 'Tipping point' or 'breaking point' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "a-bird-in-the-hand",
        "patterns": _r(r"(a\s+)?bird\s+in\s+the\s+hand(\s+is\s+worth)?"),
        "phrase": "a bird in the hand",
        "alternatives": ["a sure thing beats a possibility", "a guaranteed outcome is worth more"],
        "reason": "References trapping wild birds. 'A sure thing beats a possibility' carries the same meaning.",
        "severity": "info",
    },
    {
        "name": "eat-crow",
        "patterns": _r(r"eat(ing)?\s+crow"),
        "phrase": "eat crow",
        "alternatives": ["admit being wrong", "swallow one's pride", "accept humiliation"],
        "reason": "References eating a killed bird as humiliating punishment. 'Admit being wrong' or 'swallow one's pride' says the same thing directly.",
        "severity": "warning",
    },
    {
        "name": "fight-like-cats-and-dogs",
        "patterns": _r(r"f(ight|ights|ighting|ought)\s+like\s+cats\s+and\s+dogs"),
        "phrase": "fight like cats and dogs",
        "alternatives": ["constantly argue", "clash frequently"],
        "reason": "Animal-fighting imagery. 'Constantly argue' or 'clash frequently' says it directly.",
        "severity": "warning",
    },
    {
        "name": "take-the-bait",
        "patterns": _r(r"(?:take|taking|took)\s+the\s+bait"),
        "phrase": "take the bait",
        "alternatives": ["fall for it", "be lured in", "be deceived"],
        "reason": "References baiting hooks and traps to catch and kill animals. 'Fall for it' or 'be deceived' is more direct.",
        "severity": "info",
    },
    {
        "name": "dont-count-your-chickens",
        "patterns": _r(r"(don'?t\s+)?count(ing)?\s+your\s+chickens(\s+before)?"),
        "phrase": "don't count your chickens",
        "alternatives": ["don't assume success prematurely", "don't celebrate too early"],
        "reason": "Commodity framing of chickens as a yield to be counted. 'Don't assume success prematurely' says it directly.",
        "severity": "info",
    },
    {
        "name": "livestock",
        "patterns": _r(r"livestock"),
        "phrase": "livestock",
        "alternatives": ["farmed animals"],
        "reason": "Commodity framing that groups sentient beings as 'stock.' 'Farmed animals' keeps the meaning without the commodity framing.",
        "severity": "warning",
    },
    {
        "name": "poultry",
        "patterns": _r(r"poultry"),
        "phrase": "poultry",
        "alternatives": ["farmed birds", "chickens and turkeys"],
        "reason": "Commodity framing for farmed birds. 'Farmed birds' or the specific species keeps the meaning without the commodity framing.",
        "severity": "warning",
    },
    {
        "name": "gestation-crate",
        "patterns": _r(r"gestation\s+(crate|stall)s?"),
        "phrase": "gestation crate",
        "alternatives": ["pregnancy cage"],
        "reason": "Industry euphemism for a metal enclosure so small a pregnant sow cannot turn around for her entire 3.5-month pregnancy. 'Pregnancy cage' is accurate.",
        "severity": "warning",
    },
    {
        "name": "depopulation",
        "patterns": _r(r"depopulat(ion|ed|ing)"),
        "phrase": "depopulation",
        "alternatives": ["mass killing", "killed en masse"],
        "reason": "Industry euphemism for killing entire flocks or herds at once. 'Mass killing' is the accurate term. (Suppressed in database or population-statistics contexts where the word refers to removing records.)",
        "severity": "warning",
    },
    {
        "name": "processing-plant",
        "patterns": _r(r"(meat[\s-]?packing|meat|packing|processing)\s+(plant|facility)s?"),
        "phrase": "processing plant",
        "alternatives": ["slaughterhouse"],
        "reason": "Industry euphemisms for slaughterhouse. 'Slaughterhouse' is the accurate term. (Suppressed in clearly non-animal contexts like data or chemical processing.)",
        "severity": "warning",
    },
    {
        "name": "farrowing-crate",
        "patterns": _r(r"farrowing\s+(crate|stall)s?"),
        "phrase": "farrowing crate",
        "alternatives": ["birthing cage"],
        "reason": "Industry euphemism for the metal cage confining a sow during birth and nursing. 'Birthing cage' is accurate.",
        "severity": "warning",
    },
    {
        "name": "battery-cage",
        "patterns": _r(r"battery[\s-]cage[ds]?"),
        "phrase": "battery cage",
        "alternatives": ["small wire cage", "confined cage"],
        "reason": "Industry euphemism for wire enclosures that give each hen less floor space than a sheet of paper. 'Small wire cage' describes what it is.",
        "severity": "warning",
    },
    {
        "name": "spent-hen",
        "patterns": _r(r"spent\s+hens?"),
        "phrase": "spent hen",
        "alternatives": ["hen killed after egg production declines"],
        "reason": "'Spent' frames the hen as a depleted resource. Naming what actually happens — she is killed when her egg production falls — is more accurate.",
        "severity": "warning",
    },
    {
        "name": "humane-slaughter",
        "patterns": _r(r"humane(ly)?\s+(slaughter(ed)?|killing|death)"),
        "phrase": "humane slaughter",
        "alternatives": ["slaughter", "killing"],
        "reason": "Industry oxymoron — a killing cannot be 'humane' to the one being killed. Drop the modifier and use 'slaughter' or 'killing.'",
        "severity": "warning",
    },
    {
        "name": "broiler-chicken",
        "patterns": _r(r"broiler\s+(chickens?|hens?)|broilers"),
        "phrase": "broiler chicken",
        "alternatives": ["chicken raised for meat"],
        "reason": "Industry term that defines a chicken by its commercial purpose. 'Chicken raised for meat' is the human-readable version. (The kitchen appliance is not flagged.)",
        "severity": "warning",
    },
    {
        "name": "dont-be-a-chicken",
        "patterns": _r(r"don'?t\s+be\s+a\s+chicken"),
        "phrase": "don't be a chicken",
        "alternatives": ["don't hesitate", "be brave", "go for it"],
        "reason": "Uses a chicken as an insult for cowardice. 'Don't hesitate' or 'be brave' is direct and doesn't rely on a demeaning stereotype.",
        "severity": "error",
    },
    {
        "name": "badger-someone",
        "patterns": _r(r"badger(ed|ing|s)?"),
        "phrase": "badger someone",
        "alternatives": ["pester", "pressure", "harass"],
        "reason": "Comes from badger-baiting, a blood sport where dogs were set on captive badgers. 'Pester' or 'pressure' carries the same meaning without the origin.",
        "severity": "info",
    },
    {
        "name": "ferret-out",
        "patterns": _r(r"ferret(ed|ing)?\s+out"),
        "phrase": "ferret out",
        "alternatives": ["uncover", "discover", "dig up"],
        "reason": "Refers to the historical use of ferrets to flush rabbits out of burrows to be killed. 'Uncover' or 'dig up' works just as well.",
        "severity": "info",
    },
    {
        "name": "cattle-vs-pets",
        "patterns": _r(r"cattle[,]?\s+(not|vs\.?|versus)\s+pets|pets\s+not\s+cattle"),
        "phrase": "cattle vs. pets",
        "alternatives": ["ephemeral vs. persistent", "disposable vs. unique", "numbered vs. named"],
        "reason": "Infrastructure metaphor that Google's own style guide flags for removal as 'figurative language that relates to the slaughter of animals.' 'Ephemeral vs. persistent' or 'disposable vs. unique' captures the same architectural concept.",
        "severity": "warning",
    },
    {
        "name": "canary-in-a-coal-mine",
        "patterns": _r(r"canary\s+in\s+(a|the)\s+coal\s+mine"),
        "phrase": "canary in a coal mine",
        "alternatives": ["early warning signal", "leading indicator", "sentinel"],
        "reason": "Refers to canaries historically placed in coal mines to die first as a warning to miners. 'Early warning signal' or 'sentinel' conveys the meaning without the harm.",
        "severity": "info",
    },
    {
        "name": "fishing-expedition",
        "patterns": _r(r"fishing\s+expeditions?"),
        "phrase": "fishing expedition",
        "alternatives": ["exploratory investigation", "speculative inquiry", "unfocused search"],
        "reason": "Frames speculative inquiry as fishing — the metaphor softens the catch. 'Exploratory investigation' is clearer, especially in legal writing.",
        "severity": "warning",
    },
    {
        "name": "sacred-cow",
        "patterns": _r(r"sacred\s+cows?"),
        "phrase": "sacred cow",
        "alternatives": ["unquestioned belief", "untouchable topic", "protected assumption"],
        "reason": "Treats cattle as objects in an 'untouchable' metaphor while also trivializing Hindu beliefs. 'Unquestioned belief' or 'protected assumption' avoids both issues.",
        "severity": "warning",
    },
    {
        "name": "scapegoat",
        "patterns": _r(r"scapegoat(ed|ing|s)?"),
        "phrase": "scapegoat",
        "alternatives": ["blame target", "fall person", "wrongly blamed"],
        "reason": "Originates from the ritual sacrifice of goats to carry away blame. 'Blame target' or 'wrongly blamed' is more precise.",
        "severity": "warning",
    },
    {
        "name": "dead-cat-bounce",
        "patterns": _r(r"dead[\s_-]?cat[\s_-]?bounce"),
        "phrase": "dead cat bounce",
        "alternatives": ["temporary rebound", "false recovery", "brief uptick"],
        "reason": "A financial term built on the image of a dead cat. 'Temporary rebound' or 'false recovery' is more professional and avoids the image.",
        "severity": "warning",
    },
    {
        "name": "dog-eat-dog",
        "patterns": _r(r"dog[\s-]eat[\s-]dog"),
        "phrase": "dog-eat-dog",
        "alternatives": ["ruthlessly competitive", "cutthroat", "fiercely competitive"],
        "reason": "Frames dogs as inherently violent toward each other as a model for competition. 'Ruthlessly competitive' or 'cutthroat' conveys the meaning without the stereotype.",
        "severity": "info",
    },
    {
        "name": "whack-a-mole",
        "patterns": _r(r"whack[\s-]a[\s-]mole"),
        "phrase": "whack-a-mole",
        "alternatives": ["recurring problem", "endless loop", "unwinnable game"],
        "reason": "References a game built around repeatedly striking animals as they pop up. 'Recurring problem' or 'endless loop' describes the pattern more precisely.",
        "severity": "info",
    },
    {
        "name": "cash-cow",
        "patterns": _r(r"cash\s+cows?"),
        "phrase": "cash cow",
        "alternatives": ["moneymaker", "profit center", "reliable revenue source"],
        "reason": "Treats a cow as a thing to be extracted from for profit. 'Moneymaker' or 'profit center' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "sacrificial-lamb",
        "patterns": _r(r"sacrificial\s+lambs?"),
        "phrase": "sacrificial lamb",
        "alternatives": ["expendable person", "person set up to fail", "someone sacrificed for others"],
        "reason": "References the ritual slaughter of lambs. 'Expendable person' or 'someone sacrificed for others' communicates the metaphor directly.",
        "severity": "warning",
    },
    {
        "name": "sitting-duck",
        "patterns": _r(r"sitting\s+ducks?"),
        "phrase": "sitting duck",
        "alternatives": ["easy target", "vulnerable target", "exposed"],
        "reason": "Hunting imagery — a duck in the open, easy to shoot. 'Easy target' or 'vulnerable target' says the same thing.",
        "severity": "warning",
    },
    {
        "name": "open-season",
        "patterns": _r(r"open\s+season"),
        "phrase": "open season",
        "alternatives": ["free-for-all", "unrestricted criticism", "no holds barred"],
        "reason": "Refers to the legal hunting period when killing animals is permitted. 'Free-for-all' or 'no holds barred' conveys the meaning without the hunting framing.",
        "severity": "warning",
    },
    {
        "name": "put-out-to-pasture",
        "patterns": _r(r"put(s|ting)?(\s+(him|her|them))?\s+out\s+to\s+pasture"),
        "phrase": "put out to pasture",
        "alternatives": ["retire", "phase out", "sunset"],
        "reason": "Refers to the farm practice of disposing of animals once they're no longer productive. 'Retire,' 'phase out,' or 'sunset' is clearer and carries no harm.",
        "severity": "warning",
    },
    {
        "name": "dead-duck",
        "patterns": _r(r"dead\s+ducks?"),
        "phrase": "dead duck",
        "alternatives": ["lost cause", "doomed effort", "foregone conclusion"],
        "reason": "Hunting imagery — a duck that has been shot and killed. 'Lost cause' or 'doomed effort' is just as expressive.",
        "severity": "info",
    },
    {
        "name": "cull",
        "patterns": _r(r"cull(ed|ing|s)?"),
        "phrase": "cull",
        "alternatives": ["remove", "prune", "trim", "filter out"],
        "reason": "Euphemism used in wildlife management and farming for mass killing. 'Remove', 'prune', 'trim', or 'filter out' is accurate in technical contexts.",
        "severity": "warning",
    },
    {
        "name": "veal",
        "patterns": _r(r"veal(\s+cal(f|ves))?"),
        "phrase": "veal",
        "alternatives": ["calf flesh", "calf meat"],
        "reason": "'Veal' softens 'slaughtered-calf flesh' via a Norman-French borrowing. In advocacy or industry-critical writing, 'calf flesh' names what it is. (Suppressed in recipes and cooking contexts.)",
        "severity": "info",
    },
    {
        "name": "lame-duck",
        "patterns": _r(r"lame[\s-]duck"),
        "phrase": "lame duck",
        "alternatives": ["outgoing", "transitional", "ineffective"],
        "reason": "Combines an ableist adjective with a reference to a bird unable to fly due to injury. 'Outgoing', 'transitional', or 'ineffective' is more precise.",
        "severity": "info",
    },
    {
        "name": "debeaking",
        "patterns": _r(r"debeak(ing|ed)|beak\s+(trimming|trim|conditioning)"),
        "phrase": "debeaking",
        "alternatives": ["beak amputation", "beak mutilation"],
        "reason": "Industry euphemism for slicing or burning off hens' beaks, typically without anesthesia. 'Beak amputation' names what actually happens.",
        "severity": "warning",
    },
    {
        "name": "dehorning",
        "patterns": _r(r"dehorn(ing|ed)|disbud(ding|ded)"),
        "phrase": "dehorning",
        "alternatives": ["horn amputation", "horn removal"],
        "reason": "Industry term for removing cattle horns, typically without anesthesia. 'Horn amputation' is accurate.",
        "severity": "warning",
    },
    {
        "name": "tail-docking",
        "patterns": _r(r"tail[\s-]docking|tail\s+docked|docked\s+tail"),
        "phrase": "tail docking",
        "alternatives": ["tail amputation"],
        "reason": "Amputating pigs', sheep's, or dogs' tails. 'Tail amputation' is the accurate term.",
        "severity": "warning",
    },
    {
        "name": "ear-notching",
        "patterns": _r(r"ear[\s-]notch(ing|ed)"),
        "phrase": "ear notching",
        "alternatives": ["ear mutilation"],
        "reason": "Industry identification practice of cutting notches in animals' ears. 'Ear mutilation' names what it is.",
        "severity": "info",
    },
    {
        "name": "ventilation-shutdown",
        "patterns": _r(r"ventilation\s+shutdown(\s+plus)?|VSD\+|VSD\s+plus"),
        "phrase": "ventilation shutdown",
        "alternatives": ["mass killing by suffocation", "heat-and-suffocation killing"],
        "reason": "Industry term for killing entire flocks by cutting off airflow — the animals die from suffocation and heat. 'Mass killing by suffocation' is the accurate term. (Suppressed in HVAC contexts.)",
        "severity": "warning",
    },
    {
        "name": "maceration",
        "patterns": _r(r"(maceration\s+of\s+chicks|chick\s+maceration|macerat(ed|ing)\s+chicks)"),
        "phrase": "maceration of chicks",
        "alternatives": ["grinding newborn chicks alive", "chick grinding"],
        "reason": "Industry euphemism for killing day-old male chicks by grinding them alive. Say what the process is. (Bare 'maceration' in culinary or chemistry contexts is not flagged.)",
        "severity": "warning",
    },
    {
        "name": "abattoir",
        "patterns": _r(r"abattoirs?"),
        "phrase": "abattoir",
        "alternatives": ["slaughterhouse"],
        "reason": "French-derived euphemism for slaughterhouse. 'Slaughterhouse' is the accurate English term.",
        "severity": "warning",
    },
    {
        "name": "rendering-plant",
        "patterns": _r(r"rendering\s+(plant|facility)s?"),
        "phrase": "rendering plant",
        "alternatives": ["animal-body processing plant", "carcass-processing facility"],
        "reason": "Facility that processes animal bodies — roadkill, downed animals, slaughter byproducts — into meal, fat, and tallow. Naming it accurately makes the supply chain visible. (Only the full compound 'rendering plant' / 'rendering facility' is flagged; bare 'rendering' for graphics or UI is not.)",
        "severity": "info",
    },
    {
        "name": "stockyard",
        "patterns": _r(r"stockyards?"),
        "phrase": "stockyard",
        "alternatives": ["slaughterhouse pens", "live-animal market"],
        "reason": "Euphemism for pre-slaughter holding pens. 'Slaughterhouse pens' describes what the facility actually is.",
        "severity": "info",
    },
    {
        "name": "laying-hen",
        "patterns": _r(r"(laying|layer)\s+hens?"),
        "phrase": "laying hen",
        "alternatives": ["hen"],
        "reason": "Defines a hen by her egg-laying function. When sex and species are relevant, 'hen' is sufficient.",
        "severity": "warning",
    },
    {
        "name": "use-category-naming",
        "patterns": _r(r"(dairy|beef)\s+(cow|cows|cattle)|meat\s+(birds?|rabbits?|goats?)"),
        "phrase": "dairy cow",
        "alternatives": ["cow", "the species name alone"],
        "reason": "Defines an animal by the product humans extract from them. The species name alone is sufficient unless the use is actively relevant.",
        "severity": "warning",
    },
    {
        "name": "brood-sow",
        "patterns": _r(r"brood\s+sows?|breeding\s+(stock|pair)"),
        "phrase": "brood sow",
        "alternatives": ["pregnant pig", "nursing mother pig"],
        "reason": "Defines a female animal by her reproductive function. Name the individual directly where possible.",
        "severity": "warning",
    },
    {
        "name": "cattle-call",
        "patterns": _r(r"cattle\s+calls?"),
        "phrase": "cattle call",
        "alternatives": ["open call", "mass audition"],
        "reason": "Likens human applicants to livestock being herded. 'Open call' or 'mass audition' carries the same meaning without the framing.",
        "severity": "warning",
    },
    {
        "name": "pet-project",
        "patterns": _r(r"pet\s+projects?"),
        "phrase": "pet project",
        "alternatives": ["side project", "passion project"],
        "reason": "Carries over the property framing of 'pet' (something owned) to the project. 'Side project' or 'passion project' captures the same idea without the ownership framing.",
        "severity": "info",
    },
    {
        "name": "humanely-raised",
        "patterns": _r(r"humanely\s+(raised|produced|farmed)"),
        "phrase": "humanely raised",
        "alternatives": ["factory-farmed", "raised in [specific conditions]"],
        "reason": "USDA-unregulated marketing label — companies define their own standards, and the actual conditions often differ little from factory farming. Describe the actual conditions where possible.",
        "severity": "warning",
    },
    {
        "name": "free-range",
        "patterns": _r(r"free[\s-]rang(e|ing)|free[\s-]roaming"),
        "phrase": "free-range",
        "alternatives": ["minimally accessible outdoor pen", "outdoor access (USDA minimum)"],
        "reason": "USDA requires only 'access to outdoors' — often a small door to a small porch that most birds never use. The label does not guarantee meaningful outdoor life.",
        "severity": "warning",
    },
    {
        "name": "pasture-raised",
        "patterns": _r(r"pasture[\s-]raised|pastured"),
        "phrase": "pasture-raised",
        "alternatives": ["raised on pasture (certifier-dependent)"],
        "reason": "Not USDA-regulated; the meaning depends on whichever certifier the producer chooses. Name the certifier and the actual conditions where possible.",
        "severity": "warning",
    },
    {
        "name": "grass-fed",
        "patterns": _r(r"grass[\s-](fed|finished)"),
        "phrase": "grass-fed",
        "alternatives": ["grass-fed (USDA definition dropped 2016)", "forage-finished"],
        "reason": "Describes the cattle's feed, not their welfare. Slaughter, transport, and mother-calf separation happen the same way. The USDA dropped its 'grass-fed' definition in 2016; current usage is producer-defined.",
        "severity": "info",
    },
    {
        "name": "cage-free-for-meat",
        "patterns": _r(r"cage[\s-]free\s+(chicken|turkey|meat|pork|beef)"),
        "phrase": "cage-free chicken",
        "alternatives": ["crowded indoor housing", "barn-raised"],
        "reason": "Meaningless for meat birds — broiler chickens and turkeys are almost never caged in industrial production. The label implies a welfare improvement that doesn't exist. (Cage-free for eggs IS a meaningful distinction; that usage is not flagged.)",
        "severity": "warning",
    },
    {
        "name": "humane-certifications",
        "patterns": _r(r"Certified\s+Humane|Animal\s+Welfare\s+Approved|Global\s+Animal\s+Partnership|American\s+Humane\s+Certified|One\s+Health\s+Certified|GAP\s+(certified|Step(\s+\d)?)"),
        "phrase": "Certified Humane",
        "alternatives": ["name the certifier and standard"],
        "reason": "Third-party welfare certifications with widely varying standards — some are meaningful (Animal Welfare Approved), others are marketing (American Humane Certified). Name the specific standard if relevant.",
        "severity": "info",
    },
    {
        "name": "ethically-sourced-animal",
        "patterns": _r(r"(ethically|responsibly)\s+sourced\s+(meat|dairy|eggs|beef|pork|chicken)|happy\s+(meat|cows?)"),
        "phrase": "ethically sourced meat",
        "alternatives": ["describe the actual farm practices"],
        "reason": "Marketing language without a standard definition when applied to animal products. 'Ethically sourced' meat has no USDA definition. Describe the actual practices instead. (The phrase applied to coffee, chocolate, or textiles is not flagged.)",
        "severity": "info",
    },
    {
        "name": "dolphin-safe",
        "patterns": _r(r"dolphin[\s-]safe|line[\s-]caught|pole[\s-](and[\s-]line[\s-])?caught|sustainab(ly\s+caught|le\s+seafood)"),
        "phrase": "dolphin-safe",
        "alternatives": ["name the specific fishing method and bycatch statistics"],
        "reason": "Addresses specific bycatch concerns but not fish suffering. Fish feel pain, suffocate on deck, or are crushed in nets regardless of how the boat avoids catching dolphins or catches fish one at a time.",
        "severity": "info",
    },
    {
        "name": "feed-to-predators",
        "patterns": _r(r"(feed|fed|feeding)\s+to\s+the\s+(lions|sharks|dogs)"),
        "phrase": "feed to the lions",
        "alternatives": ["sacrifice", "leave exposed", "abandon to attack"],
        "reason": "Human-as-prey imagery. 'Sacrifice' or 'leave exposed' captures the same meaning.",
        "severity": "error",
    },
    {
        "name": "pig-to-slaughter",
        "patterns": _r(r"(like\s+(a\s+)?)?pigs?\s+to\s+slaughter"),
        "phrase": "like a pig to slaughter",
        "alternatives": ["defenseless", "walking into disaster"],
        "reason": "Direct slaughter imagery. 'Defenseless' or 'walking into disaster' captures the same meaning.",
        "severity": "error",
    },
    {
        "name": "turkey-shoot",
        "patterns": _r(r"turkey[\s-]shoot"),
        "phrase": "turkey shoot",
        "alternatives": ["trivially easy win", "no-contest situation", "walkover"],
        "reason": "One-sided-slaughter imagery for an easy win. 'Walkover' or 'trivially easy win' carries the same meaning.",
        "severity": "error",
    },
    {
        "name": "fox-guarding-henhouse",
        "patterns": _r(r"fox(es)?\s+(guarding\s+the|in\s+the)\s+hen[\s-]?house"),
        "phrase": "fox guarding the henhouse",
        "alternatives": ["conflict of interest", "the wrong person in charge"],
        "reason": "Frames predation as an inevitable natural order. 'Conflict of interest' or 'wrong person in charge' is the actual point being made.",
        "severity": "warning",
    },
    {
        "name": "bull-in-china-shop",
        "patterns": _r(r"(like\s+a\s+)?bull\s+in\s+a\s+china\s+shop"),
        "phrase": "bull in a china shop",
        "alternatives": ["tornado in a glass factory", "clumsy disruption", "careless and destructive"],
        "reason": "Bull-as-clumsy-brute stereotype — actually originates from a cartoon, not reality. 'Clumsy disruption' or 'careless and destructive' is more accurate.",
        "severity": "warning",
    },
    {
        "name": "build-a-better-mousetrap",
        "patterns": _r(r"build(s|ing)?\s+a\s+better\s+mousetrap|better\s+mousetrap"),
        "phrase": "build a better mousetrap",
        "alternatives": ["build a better mouse pad", "invent something better"],
        "reason": "Mouse-killing device as innovation metaphor. 'Invent something better' or 'build a better mouse pad' captures the idea.",
        "severity": "warning",
    },
    {
        "name": "packed-like-sardines",
        "patterns": _r(r"(packed|squeezed)\s+(in\s+)?like\s+sardines"),
        "phrase": "packed like sardines",
        "alternatives": ["packed in like pickles", "tightly crowded", "crammed together"],
        "reason": "Accurately describes industrial fishing and canning — the 'imagery' is the reality. 'Tightly crowded' or 'packed in like pickles' works without invoking it.",
        "severity": "warning",
    },
    {
        "name": "pull-the-wool",
        "patterns": _r(r"pull(s|ing|ed)?\s+the\s+wool\s+over"),
        "phrase": "pull the wool over",
        "alternatives": ["deceive", "mislead", "pull the polyester over your eyes"],
        "reason": "Wool (sheep exploitation) as a deception metaphor. 'Deceive' or 'mislead' is direct and clearer.",
        "severity": "warning",
    },
    {
        "name": "lipstick-on-a-pig",
        "patterns": _r(r"(put(s|ting)?\s+)?lipstick\s+on\s+a\s+pig"),
        "phrase": "lipstick on a pig",
        "alternatives": ["superficially improve", "disguise the flaw", "dress up a bad product"],
        "reason": "Frames pigs as ugly objects. 'Superficially improve' or 'disguise the flaw' is the actual meaning.",
        "severity": "warning",
    },
    {
        "name": "silk-purse-sows-ear",
        "patterns": _r(r"silk\s+purse\s+(out\s+of|from)\s+a\s+sow's\s+ear"),
        "phrase": "silk purse out of a sow's ear",
        "alternatives": ["diamond bracelet out of a lump of coal", "transform something unpromising"],
        "reason": "Pig body parts framed as worthless. 'Transform something unpromising' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "black-sheep",
        "patterns": _r(r"black\s+sheep"),
        "phrase": "black sheep",
        "alternatives": ["outlier", "misfit", "odd one out"],
        "reason": "Commodifies sheep coat color as a family-shame metaphor, with racial baggage. 'Outlier' or 'odd one out' works.",
        "severity": "warning",
    },
    {
        "name": "wolf-in-sheeps-clothing",
        "patterns": _r(r"wol(f|ves)\s+in\s+sheep'?s\s+clothing"),
        "phrase": "wolf in sheep's clothing",
        "alternatives": ["deceiver in disguise", "hidden threat", "threat wearing a friendly face"],
        "reason": "Wolves-as-deceivers trope. 'Hidden threat' or 'deceiver in disguise' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "chicken-out",
        "patterns": _r(r"chicken(s|ed|ing)\s+out|chicken\s+out"),
        "phrase": "chicken out",
        "alternatives": ["back out", "lose nerve", "get cold feet"],
        "reason": "Chicken-as-coward framing. 'Back out' or 'lose nerve' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "feeding-frenzy",
        "patterns": _r(r"feeding\s+frenz(y|ies)"),
        "phrase": "feeding frenzy",
        "alternatives": ["chaotic rush", "scramble to exploit", "uncontrolled grab"],
        "reason": "Shark-predation imagery used for human behavior. 'Chaotic rush' or 'scramble to exploit' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "blood-in-the-water",
        "patterns": _r(r"(smell[s]?\s+)?blood\s+in\s+the\s+water"),
        "phrase": "blood in the water",
        "alternatives": ["signs of weakness", "vulnerability visible", "sensing a kill"],
        "reason": "Shark-predation imagery. 'Signs of weakness' or 'vulnerability visible' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "circling-vultures",
        "patterns": _r(r"(circl(e|ing)\s+(like\s+)?vultures|vultures\s+circling)"),
        "phrase": "circling like vultures",
        "alternatives": ["waiting to exploit", "hovering opportunistically", "waiting for weakness"],
        "reason": "Species defamation — the 'circling vulture' framing is factually wrong (vultures are ecological cleaners, not predators) and has driven real persecution; vulture populations are crashing globally. 'Waiting to exploit' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "madder-than-wet-hen",
        "patterns": _r(r"mad(der)?\s+(than|as)\s+a\s+wet\s+hen"),
        "phrase": "madder than a wet hen",
        "alternatives": ["furious", "livid", "seething"],
        "reason": "References the farm practice of dunking broody hens in water to break their nesting instinct. 'Furious' or 'livid' says it directly.",
        "severity": "warning",
    },
    {
        "name": "code-monkey",
        "patterns": _r(r"code\s+monkeys?"),
        "phrase": "code monkey",
        "alternatives": ["developer", "programmer", "engineer"],
        "reason": "Frames programmers as trained animals, and compounds with the long history of 'monkey' used as a racial slur. 'Developer' or 'engineer' is the accurate term.",
        "severity": "warning",
    },
    {
        "name": "hog-resource",
        "patterns": _r(r"(memory|CPU|bandwidth|resource|disk|space)\s+hog|hogging\s+(memory|CPU|bandwidth|resources|the)|hogs\s+the|hog\s+the\s+spotlight"),
        "phrase": "memory hog",
        "alternatives": ["resource-intensive", "heavy consumer", "monopolizes", "dominates"],
        "reason": "Builds on the pig-as-greedy stereotype (pigs are actually selective eaters). 'Resource-intensive' or 'monopolizes' is more accurate and avoids the framing.",
        "severity": "warning",
    },
    {
        "name": "pigheaded",
        "patterns": _r(r"pig[\s-]?headed(ness)?"),
        "phrase": "pigheaded",
        "alternatives": ["obstinate", "inflexible", "unreasonable"],
        "reason": "Pig-as-stubborn stereotype (pigs are intelligent, not stubborn). 'Obstinate' or 'unreasonable' says it directly.",
        "severity": "warning",
    },
    {
        "name": "eat-like-a-pig",
        "patterns": _r(r"eat(s|ing|e)?\s+like\s+a\s+pig|ate\s+like\s+a\s+pig|pig(s|ged|ging)?\s+out"),
        "phrase": "eat like a pig",
        "alternatives": ["overeat", "gorge", "eat voraciously"],
        "reason": "Pig-as-glutton stereotype (actually wrong — pigs are selective eaters in natural conditions). 'Overeat' or 'gorge' says the same thing.",
        "severity": "warning",
    },
    {
        "name": "son-of-a-bitch",
        "patterns": _r(r"sons?[\s-]of[\s-]a[\s-]bitch|sons\s+of\s+bitches"),
        "phrase": "son of a bitch",
        "alternatives": ["specific descriptor"],
        "reason": "Female-dog insult that compounds misogyny with species defamation. A specific descriptor is clearer and doesn't land on anyone's mother or on dogs.",
        "severity": "warning",
    },
    {
        "name": "sheeple",
        "patterns": _r(r"sheeple"),
        "phrase": "sheeple",
        "alternatives": ["conformists", "unquestioning followers", "uncritical crowd"],
        "reason": "Coined term meaning 'sheep-people' — dehumanizes the target while defaming sheep (who are actually complex social animals). 'Conformists' or 'uncritical crowd' carries the same meaning.",
        "severity": "warning",
    },
    {
        "name": "loan-shark",
        "patterns": _r(r"(loan|card)[\s-]sharks?"),
        "phrase": "loan shark",
        "alternatives": ["predatory lender", "hustler", "card hustler"],
        "reason": "Species-as-predator trope applied to exploitative humans, which misrepresents sharks and provides a convenient framing for financial harm. 'Predatory lender' or 'hustler' is direct and more accurate.",
        "severity": "warning",
    },
    {
        "name": "vulture-capitalist",
        "patterns": _r(r"vulture\s+(capitalist|capitalism|fund)s?"),
        "phrase": "vulture capitalist",
        "alternatives": ["predatory investor", "scavenger capitalist", "distressed-debt investor"],
        "reason": "Species defamation that drives real-world vulture persecution — global vulture populations are crashing largely from this kind of cultural framing. 'Predatory investor' names the behavior without defaming an ecologically critical species.",
        "severity": "warning",
    },
    {
        "name": "weasel-words",
        "patterns": _r(r"weasel\s+words?|weasel(s|ed|ing)?\s+out"),
        "phrase": "weasel words",
        "alternatives": ["evasive language", "evade", "slippery phrasing"],
        "reason": "Species-as-deceitful trope. 'Evasive language' or 'slippery phrasing' is more direct. (Wikipedia's Manual of Style uses 'weasel words' as an internal term of art; that context is suppressed.)",
        "severity": "info",
    },
    {
        "name": "leech-off",
        "patterns": _r(r"leech(es|ed|ing)?\s+off|bloodsuckers?"),
        "phrase": "leech off",
        "alternatives": ["freeload", "mooch", "exploit", "parasitic"],
        "reason": "Species-as-parasite trope. 'Freeload' or 'mooch' is direct. (Bare 'leech' in medical contexts — leeches are still used in some surgeries — is not flagged.)",
        "severity": "warning",
    },
    {
        "name": "monkey-business",
        "patterns": _r(r"monkey\s+business|monkey(s|ing|ed)?\s+around|(make|makes|making|made)\s+a\s+monkey\s+of"),
        "phrase": "monkey business",
        "alternatives": ["mischief", "fool around", "tamper with", "make a fool of"],
        "reason": "Primate-as-foolish stereotype with a long racial history. 'Mischief' or 'fool around' is direct and doesn't carry the baggage.",
        "severity": "warning",
    },
    {
        "name": "not-my-monkeys",
        "patterns": _r(r"not\s+my\s+(circus[,]?\s+not\s+my\s+monkeys?|monkeys?|circus)"),
        "phrase": "not my circus, not my monkeys",
        "alternatives": ["not my problem", "not my concern", "not my mess to clean up"],
        "reason": "Direct reference to circus-animal exploitation. 'Not my problem' carries the same meaning.",
        "severity": "info",
    },
    {
        "name": "bird-brain",
        "patterns": _r(r"bird[\s-]?brain(ed)?"),
        "phrase": "bird brain",
        "alternatives": ["forgetful", "absent-minded", "scatter-brained"],
        "reason": "Bird-as-stupid stereotype (corvids and parrots rank among the most cognitively sophisticated non-human animals). 'Forgetful' or 'absent-minded' is more accurate.",
        "severity": "info",
    },
    {
        "name": "foie-gras",
        "patterns": _r(r"foie[\s-]gras"),
        "phrase": "foie gras",
        "alternatives": ["force-fed duck liver", "force-fed goose liver"],
        "reason": "French for 'fat liver'; obscures that the product comes from force-feeding ducks or geese until their livers enlarge to ten times normal size. Name the process.",
        "severity": "warning",
    },
    {
        "name": "chevon",
        "patterns": _r(r"chevon"),
        "phrase": "chevon",
        "alternatives": ["goat flesh", "goat meat"],
        "reason": "Marketing-constructed word (coined in the 1920s) to make goat meat palatable to Anglophone consumers. 'Goat flesh' or 'goat meat' is accurate.",
        "severity": "warning",
    },
    {
        "name": "sweetbread",
        "patterns": _r(r"sweetbreads?"),
        "phrase": "sweetbread",
        "alternatives": ["calf thymus", "calf pancreas", "lamb thymus"],
        "reason": "Opaque culinary term for calf or lamb thymus or pancreas. Naming the organ is clearer. (Suppressed in recipe/cooking contexts.)",
        "severity": "info",
    },
    {
        "name": "mutton",
        "patterns": _r(r"mutton"),
        "phrase": "mutton",
        "alternatives": ["sheep flesh", "sheep meat"],
        "reason": "'Mutton' obscures the species. 'Sheep flesh' names it. (Suppressed in recipe contexts.)",
        "severity": "info",
    },
    {
        "name": "venison",
        "patterns": _r(r"venison"),
        "phrase": "venison",
        "alternatives": ["deer flesh", "deer meat"],
        "reason": "'Venison' obscures the species. 'Deer flesh' names it. (Suppressed in recipe or hunting-regulation contexts.)",
        "severity": "info",
    },
    {
        "name": "squab",
        "patterns": _r(r"squabs?"),
        "phrase": "squab",
        "alternatives": ["pigeon flesh", "young pigeon meat"],
        "reason": "Marketing term for young pigeon raised for slaughter. 'Pigeon flesh' names what it is. (Suppressed in recipe contexts.)",
        "severity": "info",
    },
    {
        "name": "spare-ribs",
        "patterns": _r(r"spare[\s-]?ribs"),
        "phrase": "spare ribs",
        "alternatives": ["pig ribs"],
        "reason": "'Spare' frames body parts as disposable/extra. 'Pig ribs' is accurate. (Suppressed in recipe/BBQ contexts.)",
        "severity": "info",
    },
    {
        "name": "leather-product",
        "patterns": _r(r"(genuine|real|top[\s-]grain|full[\s-]grain)?\s*leather"),
        "phrase": "leather",
        "alternatives": ["cow skin", "animal skin", "vegan leather", "synthetic leather", "plant leather"],
        "reason": "'Leather' obscures that the material is the skin of a killed cow (or pig, sheep, etc.). In advocacy or supply-chain writing, naming it is clearer. Suppressed in fashion/product contexts where the industry term is expected.",
        "severity": "info",
    },
    {
        "name": "wool-product",
        "patterns": _r(r"(merino\s+|lambs)?wool"),
        "phrase": "wool",
        "alternatives": ["sheep hair", "synthetic fiber", "plant fiber"],
        "reason": "'Wool' obscures that the fiber is sheep hair, usually from sheep bred for extreme coat yields (mulesing, shearing injury, eventual slaughter). Advocacy writing names it directly. Suppressed in textile/fashion contexts.",
        "severity": "info",
    },
    {
        "name": "down-feathers",
        "patterns": _r(r"down\s+(feathers|jacket|comforter|pillow|filling)|(goose|duck)\s+down"),
        "phrase": "down feathers",
        "alternatives": ["plant-based insulation", "synthetic fill", "recycled fill"],
        "reason": "Down is plucked from ducks and geese, often while alive and distressed. 'Plant-based insulation' or 'synthetic fill' describes the alternative. Bare 'down' (direction) is NOT flagged — only product compounds.",
        "severity": "info",
    },
    {
        "name": "cashmere-mohair-angora",
        "patterns": _r(r"cashmere|mohair|angora"),
        "phrase": "cashmere",
        "alternatives": ["goat hair", "rabbit hair", "recycled fiber", "synthetic alternative"],
        "reason": "Luxury-marketing names that obscure the animal source. Cashmere and mohair come from goats; angora comes from rabbits (who are often plucked live and injured). Naming the species is clearer in advocacy writing.",
        "severity": "info",
    },
    {
        "name": "silk-product",
        "patterns": _r(r"(pure\s+|mulberry\s+|raw\s+)?silk"),
        "phrase": "silk",
        "alternatives": ["plant silk", "peace silk", "synthetic silk", "recycled fiber"],
        "reason": "Silk production typically requires boiling silkworms alive inside their cocoons to prevent the thread from breaking. Peace silk, plant silk, and synthetics avoid this. Suppressed in textile/fashion contexts.",
        "severity": "info",
    },
    {
        "name": "royal-jelly-beeswax",
        "patterns": _r(r"royal\s+jelly|beeswax|propolis"),
        "phrase": "royal jelly",
        "alternatives": ["plant alternative", "candelilla wax", "carnauba wax", "soy wax"],
        "reason": "Bee products are extracted through industrial beekeeping, which involves queen-clipping, smoke stressing, and often the destruction of hives. Plant-based waxes (candelilla, carnauba, soy) serve most of the same purposes.",
        "severity": "info",
    },
    {
        "name": "downed-animal",
        "patterns": _r(r"down(ed|er)\s+(animal|cow|cattle|pig)s?"),
        "phrase": "downed animal",
        "alternatives": ["animal too sick or injured to walk", "collapsed animal"],
        "reason": "'Downed' uses passive voice to elide why the animal is on the ground — untreated injury or illness in transport or on the farm. 'Too sick to walk' names the condition.",
        "severity": "warning",
    },
    {
        "name": "forced-insemination",
        "patterns": _r(r"(artificial|forced)\s+insemination|AI\s+in\s+(cattle|cows|dairy|pigs|sheep|swine)"),
        "phrase": "artificial insemination",
        "alternatives": ["forced impregnation"],
        "reason": "Industry-standard procedure involving restraint and reproductive invasion. 'Forced impregnation' is the accurate term when the animal cannot consent. (The bare abbreviation 'AI' is not flagged — too much overlap with artificial intelligence. The rule fires only on the specific animal-ag compounds.)",
        "severity": "info",
    },
    {
        "name": "farrowing-as-process",
        "patterns": _r(r"farrow(ing|ed)"),
        "phrase": "farrowing",
        "alternatives": ["giving birth (for pigs)", "piglet-birthing"],
        "reason": "Industry verb that erases the individual animal giving birth. 'Giving birth' is the plain-language version. (The compound 'farrowing crate' is flagged by its own rule.)",
        "severity": "info",
    },
    {
        "name": "live-export",
        "patterns": _r(r"live\s+(export(s|ing)?|transport|shipment)"),
        "phrase": "live export",
        "alternatives": ["transport to slaughter", "export for slaughter"],
        "reason": "Industry term for loading animals onto ships or trucks for days-to-weeks journeys to overseas slaughter. 'Transport to slaughter' names the destination.",
        "severity": "warning",
    },
    {
        "name": "meat-industry-self-naming",
        "patterns": _r(r"(pork|beef|dairy|poultry|veal|egg)\s+industry"),
        "phrase": "pork industry",
        "alternatives": ["pig-flesh industry", "cow-flesh industry", "cow-milk industry", "chicken-flesh industry"],
        "reason": "Each term names the product rather than the species it comes from. Naming the species (e.g. 'pig-flesh industry') makes the supply chain visible. Low priority — use in advocacy writing, not general documentation.",
        "severity": "info",
    },
    {
        "name": "trophy-hunting",
        "patterns": _r(r"trophy\s+(hunt(ing|er|ers)?|kill(s)?)"),
        "phrase": "trophy hunting",
        "alternatives": ["killing for display", "recreational killing"],
        "reason": "Frames a killed animal as an achievement to be displayed. 'Killing for display' or 'recreational killing' names the activity.",
        "severity": "warning",
    },
    {
        "name": "big-game-hunter",
        "patterns": _r(r"big[\s-]game\s+hunt(ing|er|ers)?"),
        "phrase": "big-game hunting",
        "alternatives": ["large-animal hunter", "elephant/lion/rhino hunter"],
        "reason": "'Big game' frames large wild animals as sport objects existing for human recreation. 'Large-animal hunter' names it; better still, name the species (elephant, lion, rhino).",
        "severity": "warning",
    },
    {
        "name": "sport-fishing",
        "patterns": _r(r"sport[\s]?fishing|recreational\s+fishing|game\s+fishing"),
        "phrase": "sport fishing",
        "alternatives": ["recreational fishing (if literal)", "recreational killing of fish"],
        "reason": "'Sport' frames killing fish as leisure. In contexts critical of the activity, 'recreational killing of fish' is accurate. (In neutral angling-industry writing, the scanner adds noise; tune the context or disable in those files.)",
        "severity": "info",
    },
    {
        "name": "catch-and-release",
        "patterns": _r(r"catch[\s-]and[\s-]release"),
        "phrase": "catch-and-release",
        "alternatives": ["capture and release", "captured and released (with injury)"],
        "reason": "Frames hook injury, exhaustion, and stress as harmless. Studies show significant post-release mortality, especially for species caught from deep water. 'Capture and release' is more neutral.",
        "severity": "info",
    },
    {
        "name": "thin-the-herd",
        "patterns": _r(r"thin(s|ning|ned)?\s+(out\s+)?the\s+herd"),
        "phrase": "thin the herd",
        "alternatives": ["reduce numbers by killing", "kill off"],
        "reason": "Culling euphemism that softens 'kill off selected animals.' 'Kill off' says it directly.",
        "severity": "info",
    },
    {
        "name": "humane-trap-removal",
        "patterns": _r(r"humane\s+(traps?|removal|control)"),
        "phrase": "humane trap",
        "alternatives": ["non-lethal trap", "non-lethal removal", "live-catch trap"],
        "reason": "'Humane' sanitizes the practice. Say whether it's lethal or non-lethal directly — 'non-lethal trap' is clearer and testable.",
        "severity": "info",
    },
    {
        "name": "lethal-control",
        "patterns": _r(r"lethal\s+(removal|control|management)"),
        "phrase": "lethal control",
        "alternatives": ["killing program", "culling program"],
        "reason": "Bureaucratic language for killing programs. 'Killing program' says it plainly.",
        "severity": "warning",
    },
    {
        "name": "fur-facility",
        "patterns": _r(r"(fur|mink|fox)\s+(farms?|ranch(es)?)"),
        "phrase": "fur farm",
        "alternatives": ["mink confinement facility", "fox confinement facility", "fur-industry facility"],
        "reason": "'Farm' or 'ranch' evokes pastoral imagery; these are intensive confinement facilities where animals live in wire cages before being gassed or electrocuted. Name them directly.",
        "severity": "warning",
    },
    {
        "name": "fur-bearing-animal",
        "patterns": _r(r"fur[\s-]bearing\s+animals?"),
        "phrase": "fur-bearing animal",
        "alternatives": ["named species", "fur-industry species"],
        "reason": "Defines wild animals by a human use. Naming the species (foxes, minks, coyotes, bobcats, chinchillas) is clearer.",
        "severity": "info",
    },
    {
        "name": "bycatch",
        "patterns": _r(r"by[\s-]?catch"),
        "phrase": "bycatch",
        "alternatives": ["incidental killing", "non-target marine deaths"],
        "reason": "Neutralizes the massive incidental killing of non-target marine species — hundreds of thousands of dolphins, sea turtles, seabirds, and sharks each year. 'Incidental killing' names it.",
        "severity": "warning",
    },
    {
        "name": "fish-stocks",
        "patterns": _r(r"fish(ery)?\s+stocks?"),
        "phrase": "fish stocks",
        "alternatives": ["fish populations", "wild fish numbers"],
        "reason": "Commodity framing of marine life as a renewable resource. 'Fish populations' is neutral and accurate.",
        "severity": "info",
    },
    {
        "name": "aquaculture",
        "patterns": _r(r"aquaculture|fish\s+farming"),
        "phrase": "aquaculture",
        "alternatives": ["industrial fish farming", "intensive fish confinement"],
        "reason": "Neutral-sounding framing for intensive fish confinement and slaughter. In advocacy writing, 'industrial fish farming' is more accurate.",
        "severity": "info",
    },
    {
        "name": "cry-wolf",
        "patterns": _r(r"cr(y|ied|ying|ies)\s+wolf"),
        "phrase": "cry wolf",
        "alternatives": ["raise false alarms", "create alert fatigue", "sound unjustified alerts"],
        "reason": "Rooted in Aesop's fable, the phrase reinforces the wolf-as-menace framing that has driven centuries of wolf persecution. 'Raise false alarms' captures the meaning.",
        "severity": "info",
    },
    {
        "name": "pecking-order",
        "patterns": _r(r"pecking\s+orders?"),
        "phrase": "pecking order",
        "alternatives": ["hierarchy", "chain of command", "ranking"],
        "reason": "Derived from the actual behavior of hens in confinement, where crowding causes injurious pecking. 'Hierarchy' or 'chain of command' captures the same idea.",
        "severity": "warning",
    },
    {
        "name": "play-cat-and-mouse",
        "patterns": _r(r"play(s|ing|ed)?\s+cat\s+and\s+mouse|(cat\s+and\s+mouse\s+game|game\s+of\s+cat\s+and\s+mouse)"),
        "phrase": "play cat and mouse",
        "alternatives": ["drawn-out pursuit", "back-and-forth chase", "evasive pursuit"],
        "reason": "Predator-prey torture metaphor — the game is about prolonging the suffering. 'Drawn-out pursuit' captures the meaning.",
        "severity": "warning",
    },
    {
        "name": "cat-who-swallowed-canary",
        "patterns": _r(r"cat\s+(that|who)\s+(swallowed|ate)\s+the\s+canary|canary[\s-]eating\s+grin"),
        "phrase": "cat that swallowed the canary",
        "alternatives": ["smug with secret knowledge", "self-satisfied grin"],
        "reason": "Predation imagery — a dead canary is the joke's punchline. 'Smug with secret knowledge' captures it.",
        "severity": "warning",
    },
    {
        "name": "chomping-at-the-bit",
        "patterns": _r(r"(chomping|champing|chomps|champs)\s+at\s+the\s+bit"),
        "phrase": "chomping at the bit",
        "alternatives": ["eager to start", "impatient to begin", "raring to go"],
        "reason": "References the metal 'bit' forced into a horse's mouth; the phrase describes the horse's attempt to relieve it. 'Eager to start' says the same thing.",
        "severity": "info",
    },
    {
        "name": "whip-into-shape",
        "patterns": _r(r"whip(s|ped|ping)?\s+into\s+shape"),
        "phrase": "whip into shape",
        "alternatives": ["get organized", "demand discipline", "restore order"],
        "reason": "Whip-violence imagery from animal training. 'Get organized' or 'restore order' is direct. (Political 'whip' and culinary 'whip' — different usage — are suppressed.)",
        "severity": "info",
    },
    {
        "name": "whale-on",
        "patterns": _r(r"whal(e|es|ing|ed)\s+on"),
        "phrase": "whale on",
        "alternatives": ["pummel", "beat up", "hammer"],
        "reason": "Whaling (whale slaughter) as metaphor for repeated hitting. 'Pummel' or 'hammer' is direct.",
        "severity": "warning",
    },
    {
        "name": "fish-or-cut-bait",
        "patterns": _r(r"fish\s+or\s+cut\s+bait"),
        "phrase": "fish or cut bait",
        "alternatives": ["decide", "commit or move on"],
        "reason": "Fishing imagery. 'Decide' or 'commit or move on' is direct.",
        "severity": "info",
    },
    {
        "name": "pull-rabbit-out-of-hat",
        "patterns": _r(r"pull(s|ing|ed)?\s+a\s+rabbit\s+out\s+of\s+a\s+hat"),
        "phrase": "pull a rabbit out of a hat",
        "alternatives": ["pull a coin out of an ear", "magically solve", "produce unexpectedly"],
        "reason": "Stage magic often uses live rabbits kept in distressing conditions. 'Magically solve' or 'produce unexpectedly' carries the meaning without referencing the practice.",
        "severity": "info",
    },
    {
        "name": "walking-on-eggshells",
        "patterns": _r(r"walk(s|ing|ed)?\s+on\s+eggshells"),
        "phrase": "walking on eggshells",
        "alternatives": ["walking on thin ice", "treading carefully", "being extra cautious"],
        "reason": "Commodifies eggs as fragile objects; erases the laying-hen origin. 'Walking on thin ice' carries the same meaning.",
        "severity": "info",
    },
    {
        "name": "put-a-horse-out-of-misery",
        "patterns": _r(r"put\s+(a|the)\s+\S+\s+out\s+of\s+(its|their|the)\s+misery|put\s+(it|them)\s+out\s+of\s+(its|their)\s+misery|put\s+out\s+of\s+(its|their|the)\s+misery"),
        "phrase": "put a horse out of its misery",
        "alternatives": ["end the suffering", "end it mercifully", "conclude a painful situation"],
        "reason": "Horse-killing idiom. 'End the suffering' carries the same meaning without the imagery.",
        "severity": "info",
    },
    {
        "name": "kill-the-fatted-calf",
        "patterns": _r(r"kill(ing)?\s+the\s+fatted\s+calf"),
        "phrase": "kill the fatted calf",
        "alternatives": ["celebrate grandly", "roll out the red carpet", "prepare a feast"],
        "reason": "Biblical animal-sacrifice imagery (Luke 15 — the Prodigal Son). 'Celebrate grandly' or 'roll out the red carpet' carries the same meaning.",
        "severity": "info",
    },
    {
        "name": "lemming-investor",
        "patterns": _r(r"(acting\s+like\s+lemmings|lemming\s+(investor|investors|behavior)|like\s+lemmings)"),
        "phrase": "acting like lemmings",
        "alternatives": ["herd-following investor", "unquestioning crowd", "uncritical followers"],
        "reason": "Based on a Disney hoax — the 1958 'White Wilderness' staged lemmings being driven off a cliff. Lemmings don't mass-suicide. The metaphor defames the species and misleads the reader.",
        "severity": "info",
    },
    {
        "name": "maggot-insult",
        "patterns": _r(r"(you|little|filthy|dirty)\s+maggots?"),
        "phrase": "you maggot",
        "alternatives": ["specific descriptor"],
        "reason": "Degrading insect insult. Most uses in documentation are quoting dialogue or user-generated content; otherwise, use a specific descriptor.",
        "severity": "warning",
    },
    {
        "name": "swine-pejorative",
        "patterns": _r(r"(filthy|dirty|you|capitalist|fascist|bourgeois)\s+swine"),
        "phrase": "filthy swine",
        "alternatives": ["specific descriptor"],
        "reason": "Pig-as-degraded pejorative. Naming the actual trait (greedy, exploitative, corrupt) is clearer. (Bare 'swine' in medical contexts like 'swine flu' is not flagged.)",
        "severity": "info",
    },
    {
        "name": "cat-fight",
        "patterns": _r(r"cat[\s-]?fights?"),
        "phrase": "cat fight",
        "alternatives": ["heated argument", "altercation", "confrontation"],
        "reason": "Gendered insult — almost exclusively applied to women arguing, framing them as cats fighting. 'Heated argument' or 'altercation' is neutral.",
        "severity": "warning",
    },
    {
        "name": "humans-and-animals",
        "patterns": _r(r"(humans?\s+and\s+animals|animals\s+and\s+(humans?|people)|people\s+and\s+animals|man\s+and\s+beast)"),
        "phrase": "humans and animals",
        "alternatives": ["humans and non-human animals", "humans and other animals", "people and other animals"],
        "reason": "False dichotomy — humans ARE animals. The phrasing reproduces the speciesist framing animal-liberation writing opposes. 'Humans and other animals' preserves the meaning accurately.",
        "severity": "info",
    },
    {
        "name": "pet-owner",
        "patterns": _r(r"(pet|dog|cat|rabbit|bird)\s+owners?"),
        "phrase": "pet owner",
        "alternatives": ["pet guardian", "dog guardian", "cat guardian", "human companion"],
        "reason": "Property framing — 'owner' treats sentient beings as possessions. 'Guardian' preserves the legal and caregiving relationship without the property connotation. Used in legal reform jurisdictions (e.g. Boulder CO, West Hollywood) since the early 2000s.",
        "severity": "info",
    },
    {
        "name": "own-a-pet",
        "patterns": _r(r"own(s|ing|ed)?\s+a\s+(pet|dog|cat|rabbit|bird)"),
        "phrase": "own a pet",
        "alternatives": ["live with a companion animal", "share a home with", "care for a"],
        "reason": "Property framing applied to companion animals. 'Live with a dog' or 'share a home with a cat' captures the relationship without the ownership frame.",
        "severity": "info",
    },
]

# ---------------------------------------------------------------------------
# File extensions to scan
# ---------------------------------------------------------------------------

SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".md", ".yml", ".yaml",
    ".go", ".rs", ".java", ".rb", ".txt", ".rst",
    ".toml", ".sh",
}

# Directories to always skip regardless of .wokeignore
SKIP_DIRS = {".git", "node_modules", "vendor"}

# ---------------------------------------------------------------------------
# Severity ordering
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def annotation_level(severity):
    """Return the GitHub Actions annotation command for a severity string."""
    return {"error": "error", "warning": "warning", "info": "notice"}.get(severity, "notice")


# ---------------------------------------------------------------------------
# .wokeignore support — simple gitignore-style line matching
# ---------------------------------------------------------------------------

def load_ignore_patterns(root):
    """Return compiled patterns from .wokeignore, or None if the file does not exist.

    Returns None (not []) when the file is absent so callers can distinguish
    'file not found' from 'file exists but is empty'.
    """
    ignore_path = Path(root) / ".wokeignore"
    if not ignore_path.exists():
        return None
    patterns = []
    with open(ignore_path, encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            # Convert glob-style pattern to regex
            # Simple implementation: treat as substring/prefix match
            # Escape regex special chars except * and ?
            regex_str = re.escape(line).replace(r"\*", ".*").replace(r"\?", ".")
            patterns.append(re.compile(regex_str))
    return patterns


def is_ignored(path_str, ignore_patterns):
    """Return True if path_str matches any ignore pattern."""
    # Normalise to forward slashes for consistent matching
    normalised = path_str.replace("\\", "/")
    for pat in ignore_patterns:
        if pat.search(normalised):
            return True
    return False


# ---------------------------------------------------------------------------
# File walker
# ---------------------------------------------------------------------------

def iter_files(scan_paths, ignore_patterns):
    """Yield Path objects for all scannable files under scan_paths."""
    for raw_path in scan_paths:
        base = Path(raw_path)
        if not base.exists():
            print(f"::warning::scan.py: path does not exist: {raw_path}", flush=True)
            continue
        if base.is_file():
            if base.suffix in SCAN_EXTENSIONS and not is_ignored(str(base), ignore_patterns):
                yield base
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            # Prune skip dirs in-place so os.walk does not descend into them
            dirnames[:] = [
                d for d in dirnames
                if d not in SKIP_DIRS and not is_ignored(
                    str(Path(dirpath) / d), ignore_patterns
                )
            ]
            for filename in filenames:
                full = Path(dirpath) / filename
                rel = str(full)
                if full.suffix in SCAN_EXTENSIONS and not is_ignored(rel, ignore_patterns):
                    yield full


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def scan_file(path, rules):
    """Return list of (line_number, rule) for all matches in path."""
    findings = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line_num, line in enumerate(fh, start=1):
                for rule in rules:
                    for pattern in rule["patterns"]:
                        if pattern.search(line):
                            findings.append((line_num, rule))
                            break  # one finding per rule per line
    except OSError as exc:
        print(f"::warning::scan.py: could not read {path}: {exc}", flush=True)
    return findings


def format_annotation(path, line_num, rule):
    """Return a GitHub Actions workflow annotation string."""
    level = annotation_level(rule["severity"])
    phrase = rule["phrase"]
    reason = rule["reason"]
    alts = ", ".join(f'"{a}"' for a in rule["alternatives"])
    message = f'"{phrase}" \u2014 {reason} Consider: {alts}'
    return f"::{level} file={path},line={line_num}::{message}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    raw_paths = os.environ.get("INPUT_PATHS", ".").split()
    scan_paths = raw_paths if raw_paths else ["."]

    raw_severity = os.environ.get("INPUT_SEVERITY", "warning").strip().lower()
    if raw_severity not in SEVERITY_ORDER:
        print(
            f"::error::scan.py: INPUT_SEVERITY must be error, warning, or info. Got: {raw_severity!r}"
        )
        sys.exit(1)
    threshold = SEVERITY_ORDER[raw_severity]

    # Load ignore patterns: prefer cwd .wokeignore, fall back to first scan path.
    # Use explicit None check so an intentionally empty .wokeignore is respected.
    root_for_ignore = scan_paths[0] if scan_paths else "."
    cwd_patterns = load_ignore_patterns(".")
    ignore_patterns = cwd_patterns if cwd_patterns is not None else (load_ignore_patterns(root_for_ignore) or [])

    total_findings = 0
    threshold_violations = 0

    for file_path in iter_files(scan_paths, ignore_patterns):
        findings = scan_file(file_path, RULES)
        for line_num, rule in findings:
            total_findings += 1
            print(format_annotation(str(file_path), line_num, rule), flush=True)
            if SEVERITY_ORDER[rule["severity"]] <= threshold:
                threshold_violations += 1

    if total_findings == 0:
        print("No language that normalizes violence toward animals was found.", flush=True)
    else:
        print(
            f"Found {total_findings} instance(s) of language that normalizes violence toward animals.",
            flush=True,
        )

    if threshold_violations > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
