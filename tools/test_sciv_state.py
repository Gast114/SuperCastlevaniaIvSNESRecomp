"""Regression for the bridge's 16-value limit hiding the player_state field."""
import re

import sciv_play as play


class Bridge:
    def __init__(self, truncated=False):
        self.truncated = truncated
        self.calls = 0

    def eval(self, source):
        self.calls += 1
        values = ([123] if 'framecount' in source else [])
        values += [int(x) for x in re.findall(r'mainmemory\.read_u\w+\((\d+)\)', source)]
        return {'values': values[:15 if self.truncated else 16], 'paused': True}


def main():
    bridge = Bridge()
    state = play.read_state(bridge)
    assert state['frame'] == 123 and state['paused']
    assert all(state[name] == address for name, (address, _) in play.FIELDS.items())
    assert bridge.calls == 2
    try:
        play.read_state(Bridge(truncated=True))
        raise AssertionError('accepted truncated state')
    except RuntimeError:
        pass
    print('PASS: all named fields survive bridge limit; truncated reads fail')


if __name__ == '__main__':
    main()
