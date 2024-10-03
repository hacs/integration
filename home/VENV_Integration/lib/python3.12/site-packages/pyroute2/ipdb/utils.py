import os
import subprocess


def test_reachable_icmp(host):
    with open(os.devnull, 'w') as devnull:
        return subprocess.check_call(
            ['ping', '-c', '1', host], stdout=devnull, stderr=devnull
        )
