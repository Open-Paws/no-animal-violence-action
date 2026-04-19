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


RULES = [
    {
        "name": "kill-two-birds-with-one-stone",
        "patterns": _p([
            "kill two birds with one stone",
            "killing two birds with one stone",
            "killed two birds with one stone",
        ]),
        "phrase": "kill two birds with one stone",
        "alternatives": ["accomplish two things at once", "solve two problems with one action", "hit two targets with one shot"],
        "reason": "Violent animal idiom with universally clearer alternatives.",
        "severity": "error",
    },
    {
        "name": "beat-a-dead-horse",
        "patterns": _p([
            "beat a dead horse",
            "beating a dead horse",
        ]),
        "phrase": "beat a dead horse",
        "alternatives": ["belabor the point", "go over old ground", "repeat unnecessarily"],
        "reason": "Violent animal idiom — alternatives are more direct.",
        "severity": "error",
    },
    {
        "name": "more-than-one-way-to-skin-a-cat",
        "patterns": _p([
            "more than one way to skin a cat",
            "many ways to skin a cat",
            "other ways to skin a cat",
        ]),
        "phrase": "more than one way to skin a cat",
        "alternatives": ["more than one way to solve this", "multiple approaches available", "several ways to accomplish this"],
        "reason": "Violent animal idiom — alternatives are shorter and clearer.",
        "severity": "error",
    },
    {
        "name": "let-the-cat-out-of-the-bag",
        "patterns": _p([
            "let the cat out of the bag",
            "letting the cat out of the bag",
        ]),
        "phrase": "let the cat out of the bag",
        "alternatives": ["reveal the secret", "disclose prematurely", "let it slip"],
        "reason": "Animal idiom — alternatives are more precise.",
        "severity": "info",
    },
    {
        "name": "open-a-can-of-worms",
        "patterns": _p([
            "open a can of worms",
            "opening a can of worms",
            "opened a can of worms",
        ]),
        "phrase": "open a can of worms",
        "alternatives": ["create a complicated situation", "uncover hidden problems", "open Pandora's box"],
        "reason": "Animal idiom — alternatives communicate the idea more directly.",
        "severity": "info",
    },
    {
        "name": "wild-goose-chase",
        "patterns": _p(["wild goose chase"]),
        "phrase": "wild goose chase",
        "alternatives": ["futile search", "pointless pursuit", "fool's errand"],
        "reason": "Animal idiom — alternatives are more universally understood.",
        "severity": "info",
    },
    {
        "name": "like-shooting-fish-in-a-barrel",
        "patterns": _p(["like shooting fish in a barrel"]),
        "phrase": "like shooting fish in a barrel",
        "alternatives": ["trivially easy", "effortless"],
        "reason": "Violent animal idiom — references killing fish for sport.",
        "severity": "error",
    },
    {
        "name": "flog-a-dead-horse",
        "patterns": _p([
            "flog a dead horse",
            "flogging a dead horse",
        ]),
        "phrase": "flog a dead horse",
        "alternatives": ["belabor the point", "waste effort on a settled matter", "repeat unnecessarily"],
        "reason": "Violent animal idiom — same meaning as 'beat a dead horse'.",
        "severity": "error",
    },
    {
        "name": "there-are-bigger-fish-to-fry",
        "patterns": _p(["there are bigger fish to fry"]),
        "phrase": "there are bigger fish to fry",
        "alternatives": ["more important matters to address", "higher priorities", "bigger issues at hand"],
        "reason": "Animal idiom referencing killing fish — alternatives are more professional.",
        "severity": "info",
    },
    {
        "name": "guinea-pig",
        "patterns": _p(["guinea pig"], word_boundary=True),
        "phrase": "guinea pig",
        "alternatives": ["test subject", "first to try", "early adopter"],
        "reason": "Animal-as-experiment metaphor — alternatives are more precise in technical contexts.",
        "severity": "warning",
    },
    {
        "name": "hold-your-horses",
        "patterns": _p(["hold your horses"]),
        "phrase": "hold your horses",
        "alternatives": ["wait a moment", "slow down", "be patient"],
        "reason": "Animal idiom — alternatives are more direct.",
        "severity": "info",
    },
    {
        "name": "the-elephant-in-the-room",
        "patterns": _p(["the elephant in the room"]),
        "phrase": "the elephant in the room",
        "alternatives": ["the obvious issue", "the unaddressed problem"],
        "reason": "Animal-as-metaphor idiom — alternatives are clearer for international audiences.",
        "severity": "info",
    },
    {
        "name": "straight-from-the-horses-mouth",
        "patterns": _p(["straight from the horse's mouth"]),
        "phrase": "straight from the horse's mouth",
        "alternatives": ["directly from the source", "firsthand", "from the authority"],
        "reason": "Animal idiom — alternatives are clearer for international audiences.",
        "severity": "info",
    },
    {
        "name": "bring-home-the-bacon",
        "patterns": _p([
            "bring home the bacon",
            "bringing home the bacon",
            "brought home the bacon",
            "brings home the bacon",
        ]),
        "phrase": "bring home the bacon",
        "alternatives": ["bring home the results", "earn a living", "win the prize"],
        "reason": "Animal slaughter idiom referencing pig flesh — alternatives are equally expressive.",
        "severity": "error",
    },
    {
        "name": "take-the-bull-by-the-horns",
        "patterns": _p([
            "take the bull by the horns",
            "taking the bull by the horns",
            "took the bull by the horns",
        ]),
        "phrase": "take the bull by the horns",
        "alternatives": ["face the challenge head-on", "tackle the problem directly", "seize the opportunity"],
        "reason": "Bullfighting idiom — alternatives convey the same assertiveness without animal violence.",
        "severity": "warning",
    },
    {
        "name": "like-lambs-to-the-slaughter",
        "patterns": _p(["like lambs to the slaughter"]),
        "phrase": "like lambs to the slaughter",
        "alternatives": ["without resistance", "blindly following", "unknowingly walking into danger"],
        "reason": "Violent animal idiom directly referencing slaughter — alternatives are more descriptive.",
        "severity": "error",
    },
    {
        "name": "no-room-to-swing-a-cat",
        "patterns": _p(["no room to swing a cat"]),
        "phrase": "no room to swing a cat",
        "alternatives": ["very cramped", "extremely tight space", "barely any room"],
        "reason": "Violent animal idiom — alternatives are shorter and clearer.",
        "severity": "warning",
    },
    {
        "name": "red-herring",
        "patterns": _p(["red herring"], word_boundary=True),
        "phrase": "red herring",
        "alternatives": ["distraction", "false lead", "misleading clue"],
        "reason": "Animal-origin idiom from the practice of dragging a fish to mislead hunting dogs.",
        "severity": "info",
    },
    {
        "name": "curiosity-killed-the-cat",
        "patterns": _p(["curiosity killed the cat"]),
        "phrase": "curiosity killed the cat",
        "alternatives": ["curiosity backfired", "being nosy caused trouble", "curiosity led to trouble"],
        "reason": "Directly references killing a cat — violent animal idiom.",
        "severity": "error",
    },
    {
        "name": "like-a-chicken-with-its-head-cut-off",
        "patterns": _p(["like a chicken with its head cut off"]),
        "phrase": "like a chicken with its head cut off",
        "alternatives": ["in a panic", "running around chaotically", "in complete disarray"],
        "reason": "Graphic slaughter imagery depicting decapitation of a chicken.",
        "severity": "error",
    },
    {
        "name": "your-goose-is-cooked",
        "patterns": _p(["your goose is cooked"]),
        "phrase": "your goose is cooked",
        "alternatives": ["you're in trouble", "your fate is sealed", "it's over for you"],
        "reason": "References killing and cooking a goose as a threat metaphor.",
        "severity": "error",
    },
    {
        "name": "throw-someone-to-the-wolves",
        "patterns": _p([
            "throw someone to the wolves",
            "throwing someone to the wolves",
            "threw someone to the wolves",
        ]),
        "phrase": "throw someone to the wolves",
        "alternatives": ["abandon to criticism", "leave to face hostility alone", "sacrifice someone"],
        "reason": "References feeding a person to wolves — violent animal imagery.",
        "severity": "error",
    },
    {
        "name": "hook-line-and-sinker",
        "patterns": _p(["hook, line, and sinker"]),
        "phrase": "hook, line, and sinker",
        "alternatives": ["completely", "without question", "fell for it entirely"],
        "reason": "References hooking fish — fishing kills fish.",
        "severity": "warning",
    },
    {
        "name": "clip-someones-wings",
        "patterns": _p([
            "clip someone's wings",
            "clipping someone's wings",
            "clipped someone's wings",
        ]),
        "phrase": "clip someone's wings",
        "alternatives": ["restrict someone's freedom", "limit someone's options", "hold someone back"],
        "reason": "References wing-clipping — physical mutilation done to farmed birds.",
        "severity": "warning",
    },
    {
        "name": "the-straw-that-broke-the-camels-back",
        "patterns": _p(["the straw that broke the camel's back"]),
        "phrase": "the straw that broke the camel's back",
        "alternatives": ["the tipping point", "the breaking point", "the final provocation"],
        "reason": "References overloading a pack animal until injury.",
        "severity": "warning",
    },
    {
        "name": "a-bird-in-the-hand-is-worth-two-in-the-bush",
        "patterns": _p(["a bird in the hand is worth two in the bush"]),
        "phrase": "a bird in the hand is worth two in the bush",
        "alternatives": ["a sure thing beats a possibility", "certainty over speculation"],
        "reason": "References trapping and catching wild birds.",
        "severity": "info",
    },
    {
        "name": "eat-crow",
        "patterns": _p(["eat crow", "eating crow"], word_boundary=True),
        "phrase": "eat crow",
        "alternatives": ["admit being wrong", "swallow one's pride", "accept humiliation"],
        "reason": "References eating a killed bird as punishment — violent animal imagery.",
        "severity": "warning",
    },
    {
        "name": "fight-like-cats-and-dogs",
        "patterns": _p([
            "fight like cats and dogs",
            "fighting like cats and dogs",
            "fought like cats and dogs",
        ]),
        "phrase": "fight like cats and dogs",
        "alternatives": ["constantly argue", "clash frequently", "have constant conflict"],
        "reason": "References animal fighting — normalizes violence between animals.",
        "severity": "warning",
    },
    {
        "name": "take-the-bait",
        "patterns": _p([
            "take the bait",
            "taking the bait",
            "took the bait",
        ]),
        "phrase": "take the bait",
        "alternatives": ["fall for it", "be lured in", "be deceived"],
        "reason": "References baiting hooks to catch and kill fish.",
        "severity": "info",
    },
    {
        "name": "dont-count-your-chickens-before-they-hatch",
        "patterns": _p(["don't count your chickens before they hatch"]),
        "phrase": "don't count your chickens before they hatch",
        "alternatives": ["don't assume success prematurely", "wait for confirmed results", "don't get ahead of yourself"],
        "reason": "References farming chickens as commodity and property.",
        "severity": "info",
    },
    {
        "name": "livestock",
        "patterns": _p(["livestock"], word_boundary=True),
        "phrase": "livestock",
        "alternatives": ["farmed animals", "animals raised for food"],
        "reason": "Industry commodity framing. Defines sentient beings by their commercial function. 'Farmed animals' is factually equivalent and does not erase the subject.",
        "severity": "warning",
    },
    {
        "name": "poultry",
        "patterns": _p(["poultry"], word_boundary=True),
        "phrase": "poultry",
        "alternatives": ["farmed birds", "chickens", "chickens and turkeys"],
        "reason": "Industry commodity framing. Abstracts individual birds into a bulk commodity term. 'Farmed birds' or the specific species name is more precise.",
        "severity": "warning",
    },
    {
        "name": "gestation-crate",
        "patterns": _p(["gestation crate", "gestation crates"], word_boundary=True),
        "phrase": "gestation crate",
        "alternatives": ["pregnancy cage", "pregnancy cages"],
        "reason": "Industry euphemism for a metal enclosure so small a pregnant sow cannot turn around for her entire 3.5-month pregnancy. 'Pregnancy cage' describes what it actually is.",
        "severity": "warning",
    },
    {
        "name": "depopulation",
        "patterns": _p(["depopulation", "depopulated", "depopulating"], word_boundary=True),
        "phrase": "depopulation",
        "alternatives": ["mass killing", "killed en masse", "killing en masse"],
        "reason": "Industry euphemism for killing entire flocks or herds. Note: suppress in database or population-statistics contexts where 'depopulation' means removing data rows.",
        "severity": "warning",
    },
    {
        "name": "processing-plant",
        "patterns": _p(["processing plant", "processing plants", "processing facility", "processing facilities"], word_boundary=True),
        "phrase": "processing plant",
        "alternatives": ["slaughterhouse", "slaughterhouses"],
        "reason": "Industry euphemism. When referring to facilities that kill animals, 'slaughterhouse' is the accurate term.",
        "severity": "warning",
    },
    {
        "name": "farrowing-crate",
        "patterns": _p(["farrowing crate", "farrowing crates"], word_boundary=True),
        "phrase": "farrowing crate",
        "alternatives": ["birthing cage", "birthing cages"],
        "reason": "Industry euphemism for a metal cage that confines a sow during and after birth, preventing her from turning around or reaching her piglets.",
        "severity": "warning",
    },
    {
        "name": "battery-cage",
        "patterns": _p(["battery cage", "battery cages"], word_boundary=True),
        "phrase": "battery cage",
        "alternatives": ["small wire cage", "small wire cages", "confined cage", "confined cages"],
        "reason": "Industry euphemism for wire enclosures giving each hen less floor space than a sheet of paper. The word 'battery' obscures that this is a tiny cage stacked in rows of thousands.",
        "severity": "warning",
    },
    {
        "name": "spent-hen",
        "patterns": _p(["spent hen", "spent hens"], word_boundary=True),
        "phrase": "spent hen",
        "alternatives": ["discarded hen", "discarded hens", "hen killed after egg production declines"],
        "reason": "Industry euphemism. 'Spent' frames a living hen as a depleted resource. These hens are typically killed at 18 months when egg production drops below commercial thresholds.",
        "severity": "warning",
    },
    {
        "name": "humane-slaughter",
        "patterns": _p([
            "humane slaughter",
            "humanely slaughter",
            "humane slaughtered",
            "humanely slaughtered",
            "humane killing",
            "humanely killing",
            "humane killed",
            "humanely killed",
        ], word_boundary=True),
        "phrase": "humane slaughter",
        "alternatives": ["slaughter", "slaughtered", "killing", "killed"],
        "reason": "Industry oxymoron. The adjective 'humane' sanitizes the act. USDA 'humane slaughter' standards permit bolt guns, electrocution, and gas chambers.",
        "severity": "warning",
    },
    {
        "name": "broiler",
        "patterns": _p(["broiler", "broilers"], word_boundary=True),
        "phrase": "broiler",
        "alternatives": ["chicken raised for meat", "chickens raised for meat", "meat chicken", "meat chickens"],
        "reason": "Industry commodity term that defines a living chicken entirely by its commercial purpose.",
        "severity": "warning",
    },
    {
        "name": "dont-be-a-chicken",
        "patterns": _p(["don't be a chicken"]),
        "phrase": "don't be a chicken",
        "alternatives": ["don't hesitate", "be brave", "go for it"],
        "reason": "Animal-as-coward insult — dehumanizing idiom common in code comments.",
        "severity": "error",
    },
    {
        "name": "pig",
        # Exclude known technical terms: Apache Pig, Hadoop Pig, PIG Latin
        "patterns": [re.compile(r"(?<!apache )(?<!hadoop )(?<!\w)pig(?! latin)(?!\w)", re.IGNORECASE)],
        "phrase": "pig",
        "alternatives": ["resource-intensive", "bloated", "heavy consumer"],
        "reason": "Animal-as-insult for resource consumption — dehumanizing and imprecise.",
        "severity": "warning",
    },
    {
        "name": "cowboy-coding",
        "patterns": _p(["cowboy coding"], word_boundary=True),
        "phrase": "cowboy coding",
        "alternatives": ["undisciplined coding", "ad-hoc development", "code without process"],
        "reason": "Reinforces animal industry terminology in a technical context.",
        "severity": "info",
    },
    {
        "name": "code-monkey",
        "patterns": _p(["code monkey"], word_boundary=True),
        "phrase": "code monkey",
        "alternatives": ["developer", "programmer", "engineer"],
        "reason": "Animal-as-insult for programmers — dehumanizing and unprofessional.",
        "severity": "warning",
    },
    {
        "name": "badger-someone",
        "patterns": _p(["badger someone"], word_boundary=True),
        "phrase": "badger someone",
        "alternatives": ["pester", "pressure", "harass"],
        "reason": "From badger-baiting — a blood sport where dogs attack captive badgers.",
        "severity": "info",
    },
    {
        "name": "ferret-out",
        "patterns": _p(["ferret out"], word_boundary=True),
        "phrase": "ferret out",
        "alternatives": ["uncover", "discover", "dig up"],
        "reason": "From using ferrets to hunt rabbits out of burrows.",
        "severity": "info",
    },
    {
        "name": "cattle-vs-pets",
        "patterns": _p(["cattle vs. pets"]),
        "phrase": "cattle vs. pets",
        "alternatives": ["ephemeral vs. persistent", "disposable vs. unique", "numbered vs. named"],
        "reason": "Infrastructure metaphor that frames animals as disposable commodities — alternatives are technically more precise.",
        "severity": "warning",
    },
    {
        "name": "pet-project",
        "patterns": _p(["pet project"], word_boundary=True),
        "phrase": "pet project",
        "alternatives": ["side project", "passion project"],
        "reason": "Common idiom — flagged for awareness.",
        "severity": "info",
    },
    {
        "name": "canary-in-a-coal-mine",
        "patterns": _p(["canary in a coal mine"]),
        "phrase": "canary in a coal mine",
        "alternatives": ["early warning signal", "leading indicator", "sentinel"],
        "reason": "Animal metaphor referencing use of canaries as disposable gas detectors — alternatives are more technical.",
        "severity": "info",
    },
    {
        "name": "dogfooding",
        "patterns": _p(["dogfooding", "dogfood", "eating your own dogfood", "eat your own dogfood"], word_boundary=True),
        "phrase": "dogfooding",
        "alternatives": ["self-hosting", "eating your own cooking", "using internally"],
        "reason": "Common tech term referencing dog food — flagged for awareness.",
        "severity": "info",
    },
    {
        "name": "herding-cats",
        "patterns": _p(["herding cats"], word_boundary=True),
        "phrase": "herding cats",
        "alternatives": ["coordinating independent contributors", "managing a distributed effort", "organizing chaos"],
        "reason": "Animal metaphor — alternatives are more descriptive.",
        "severity": "warning",
    },
    {
        "name": "go-on-a-fishing-expedition",
        "patterns": _p(["go on a fishing expedition"]),
        "phrase": "go on a fishing expedition",
        "alternatives": ["exploratory investigation", "unfocused search", "speculative inquiry"],
        "reason": "Animal metaphor referencing fishing — alternatives are more precise.",
        "severity": "warning",
    },
    {
        "name": "sacred-cow",
        "patterns": _p(["sacred cow", "sacred cows"], word_boundary=True),
        "phrase": "sacred cow",
        "alternatives": ["unquestioned belief", "untouchable topic", "protected assumption"],
        "reason": "Combines animal objectification with cultural insensitivity — trivializes Hindu beliefs while treating cattle as objects.",
        "severity": "warning",
    },
    {
        "name": "scapegoat",
        "patterns": _p(["scapegoat", "scapegoated", "scapegoating"], word_boundary=True),
        "phrase": "scapegoat",
        "alternatives": ["blame target", "fall person", "wrongly blamed"],
        "reason": "Originates from ritual sacrifice of goats — alternatives are more precise.",
        "severity": "warning",
    },
    {
        "name": "rat-race",
        "patterns": _p(["rat race"], word_boundary=True),
        "phrase": "rat race",
        "alternatives": ["daily grind", "competitive treadmill", "endless hustle"],
        "reason": "Derogatory animal metaphor for futility — alternatives are more descriptive.",
        "severity": "info",
    },
    {
        "name": "dead-cat-bounce",
        "patterns": _p(["dead cat bounce"]),
        "phrase": "dead cat bounce",
        "alternatives": ["temporary rebound", "false recovery", "brief uptick"],
        "reason": "Financial/tech term depicting animal death — alternatives are more professional.",
        "severity": "warning",
    },
    {
        "name": "dog-eat-dog",
        "patterns": _p(["dog-eat-dog", "dog eat dog"], word_boundary=True),
        "phrase": "dog-eat-dog",
        "alternatives": ["ruthlessly competitive", "cutthroat", "fiercely competitive"],
        "reason": "Characterizes animals as violent toward each other — alternatives convey meaning more precisely.",
        "severity": "info",
    },
    {
        "name": "whack-a-mole",
        "patterns": _p(["whack-a-mole", "whack a mole"], word_boundary=True),
        "phrase": "whack-a-mole",
        "alternatives": ["recurring problem", "endless loop", "unwinnable game"],
        "reason": "References a game based on hitting animals — alternatives describe the pattern more precisely.",
        "severity": "info",
    },
    {
        "name": "cash-cow",
        "patterns": _p(["cash cow", "cash cows"], word_boundary=True),
        "phrase": "cash cow",
        "alternatives": ["profit center", "reliable revenue source", "money maker"],
        "reason": "Commodifies cows — treats living beings as profit generators.",
        "severity": "warning",
    },
    {
        "name": "sacrificial-lamb",
        "patterns": _p(["sacrificial lamb", "sacrificial lambs"], word_boundary=True),
        "phrase": "sacrificial lamb",
        "alternatives": ["expendable person", "person set up to fail", "someone sacrificed for others"],
        "reason": "References ritual slaughter of lambs.",
        "severity": "warning",
    },
    {
        "name": "sitting-duck",
        "patterns": _p(["sitting duck", "sitting ducks"], word_boundary=True),
        "phrase": "sitting duck",
        "alternatives": ["easy target", "vulnerable target", "exposed"],
        "reason": "References a duck in the open, easy to shoot — hunting imagery.",
        "severity": "warning",
    },
    {
        "name": "open-season",
        "patterns": _p(["open season", "opening season", "opened season"], word_boundary=True),
        "phrase": "open season",
        "alternatives": ["free-for-all", "unrestricted criticism", "no holds barred"],
        "reason": "References hunting season — the legal period for killing animals.",
        "severity": "warning",
    },
    {
        "name": "put-out-to-pasture",
        "patterns": _p(["put out to pasture"]),
        "phrase": "put out to pasture",
        "alternatives": ["retire", "phase out", "sunset"],
        "reason": "References disposing of farm animals when no longer productive.",
        "severity": "warning",
    },
    {
        "name": "dead-duck",
        "patterns": _p(["dead duck", "dead ducks"], word_boundary=True),
        "phrase": "dead duck",
        "alternatives": ["lost cause", "doomed effort", "foregone conclusion"],
        "reason": "References a duck that has been shot and killed — hunting imagery.",
        "severity": "info",
    },
    {
        "name": "kill-process",
        "patterns": _p(["kill process", "killing process", "killed process"], word_boundary=True),
        "phrase": "kill process",
        "alternatives": ["terminate the process", "stop the process", "end the process"],
        "reason": "In POSIX context this is standard; in documentation, alternatives may be clearer for non-technical audiences.",
        "severity": "info",
    },
    {
        "name": "kill-the-server",
        "patterns": _p(["kill the server", "killing the server", "killed the server"]),
        "phrase": "kill the server",
        "alternatives": ["stop the server", "shut down the server", "terminate the server"],
        "reason": "Process language — alternatives are equally clear and more professional.",
        "severity": "info",
    },
    {
        "name": "nuke",
        "patterns": _p(["nuke"], word_boundary=True),
        "phrase": "nuke",
        "alternatives": ["delete completely", "wipe clean", "remove entirely"],
        "reason": "Violent metaphor in technical context — alternatives are more professional.",
        "severity": "warning",
    },
    {
        "name": "abort",
        "patterns": _p(["abort"], word_boundary=True),
        "phrase": "abort",
        "alternatives": ["cancel", "stop", "halt"],
        "reason": "Standard technical term — flagged for awareness in non-technical contexts.",
        "severity": "info",
    },
    {
        "name": "cull",
        "patterns": _p(["cull"], word_boundary=True),
        "phrase": "cull",
        "alternatives": ["remove", "prune", "trim", "filter out"],
        "reason": "Euphemism for mass killing of animals used in wildlife management and farming.",
        "severity": "warning",
    },
    {
        "name": "master-slave",
        "patterns": _p(["master/slave"], word_boundary=True),
        "phrase": "master/slave",
        "alternatives": ["primary/replica", "leader/follower", "controller/worker"],
        "reason": "Actively being replaced across the industry — follows existing inclusive naming initiatives.",
        "severity": "warning",
    },
    {
        "name": "whitelist-blacklist",
        "patterns": _p(["whitelist/blacklist"], word_boundary=True),
        "phrase": "whitelist/blacklist",
        "alternatives": ["allowlist/denylist", "permit list/block list", "inclusion list/exclusion list"],
        "reason": "Actively being replaced — Google, Twitter, and IETF have all adopted alternatives.",
        "severity": "warning",
    },
    {
        "name": "grandfathered",
        "patterns": _p(["grandfathered"], word_boundary=True),
        "phrase": "grandfathered",
        "alternatives": ["legacy", "exempt", "pre-existing"],
        "reason": "Historically exclusionary origin — alternatives are equally clear.",
        "severity": "info",
    },
    {
        "name": "veal",
        "patterns": _p(["veal"], word_boundary=True),
        "phrase": "veal",
        "alternatives": ["calf flesh", "flesh from calves"],
        "reason": "Industry euphemism for the flesh of male dairy calves, typically killed within weeks of birth. Obscures both the species and the age of the individual.",
        "severity": "warning",
    },
    {
        "name": "lame-duck",
        "patterns": _p(["lame duck", "lame-duck"], word_boundary=True),
        "phrase": "lame duck",
        "alternatives": ["outgoing", "transitional", "ineffective"],
        "reason": "References a bird unable to fly due to injury. 'Outgoing' or 'transitional' are more precise in political and tech contexts.",
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
