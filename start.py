#!/usr/bin/python3
from scripts.config import EVE_IS_PRESENT
from scripts.config import N_QUBITS
import os

os.system("simulaqron reset --force")
os.system("simulaqron stop")

os.system("simulaqron set max-qubits %d" % N_QUBITS)
os.system("simulaqron set max-registers %d" % (N_QUBITS * 3))
os.system("simulaqron set recv-timeout %d" % 100000)


if EVE_IS_PRESENT:
    os.system("simulaqron start --force --nodes Alice,Eve,Bob")
    os.system("xfce4-terminal -e 'bash -c \"python3 scripts/Eve.py; cat\"'&")
else:
    os.system("simulaqron start --force --nodes Alice,Bob")

os.system("xfce4-terminal -e 'bash -c \"python3 scripts/Alice.py; cat\"'&")
os.system("xfce4-terminal -e 'bash -c \"python3 scripts/Bob.py; cat\"'&")
