""" Language Parser """

from pprint import pprint

STRINGS = [
    'I beat ecalder in sf4',
    'me and evan calder beat the killers in ping pong',
    'arnold tsang beat me in sf4',
    'ecalder and icombs beat me and actsang in ping pong',
    'bdixon over atsang in street fighter 3',
    'bdixon lost to evan calder on ping pong',
    'i lost to evan calder on ping pong',
]


def parse(s):
    string = s.lower()
    string = string.replace(' in ', ' on ')
    string = string.replace(' over ', ' beat ')
    string = string.replace(' lost to ', ' lost ')

    obj = {
        'ladder': None,
        'red': [],
        'blu': [],
        'winner': 'red',
    }

    string, ladder = string.split(' on ')
    obj['ladder'] = ladder

    teams = string.split(' beat ')
    if len(teams) == 1:
        # try lost
        teams = string.split(' lost ')
        if len(teams) == 2:
            obj['winner'] = 'blu'

    obj['red'] = teams[0]
    obj['blu'] = teams[1]

    return obj


def main():
    for s in STRINGS:
        pprint(parse(s))


if __name__ == "__main__":
    main()