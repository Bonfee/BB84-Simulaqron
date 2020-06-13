from cqc.pythonLib import CQCConnection, qubit

import random, progressbar, time, itertools, requests, json, sys, hashlib
from config import N_QUBITS as N
from config import VERBOSE
from config import BOB_CLASSICAL_RECIPIENT
from config import CIPHER

if CIPHER == 'AES':
    from Crypto.Cipher import AES
    from Crypto import Random
    from Crypto.Util.Padding import pad

from base64 import b64encode

if __name__ == '__main__':

    # Initialize CQCConnection as Bob
    with CQCConnection("Bob") as Bob:

        # Receive and measure qubits
        qubits = []
        print("\n[+] Bob: [Receiving and measuring %d qubits]" % N)
        bar = progressbar.ProgressBar(maxval=N, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        bar.start()
        for i in range(N):
            qubit = Bob.recvQubit()

            bar.update(i+1)

            # Choose random basis to measure the qubit in
            base = random.randint(0, 1)

            if base == 1:
                qubit.H()
            qubits.append((qubit, qubit.measure(), base))
        bar.finish()
        print("[+] Bob: [Received and measured %d qubits]\n" % N)

        # Send used basis to Alice
        Bob.sendClassical(BOB_CLASSICAL_RECIPIENT, b''.join(str(qubit[2]).encode() for qubit in qubits))

        print('[+] Sending used basis to Alice')

        # Receive qubits' indexes to discard, use [:-1] to remove the last -
        index_to_discard = [int(_) for _ in Bob.recvClassical(msg_size=N*4).decode()[:-1].split('-')]

        print('[+] Received invalid basis to discard')

        # Remove invalid qubits
        qubits = [qubits[i] for i in range(N) if i not in index_to_discard]

        # Choose random qubits to send to Alice
        qubits_left = len(qubits)
        to_discard = qubits_left//2

        randoms = random.sample(range(qubits_left), to_discard)

        Bob.sendClassical(BOB_CLASSICAL_RECIPIENT, b''.join(("%d-%d-" % (i, qubits[i][1])).encode() for i in randoms))

        print('[+] Sending half of my supposedly secure bits to Alice')

        try:
            message = Bob.recvClassical().decode()
            if message == 'abort':
                print('[!!] Ok, we are getting intercepted... abort')
                sys.exit(0)
        except TimeoutError:
            print('Timeout Error, maybe check simulaqron recv-retry-time ?')
            pass
        except SystemExit:
            input()
        
        print("[!] Received Alice's confirmation")

        qubits = [qubits[i] for i in range(qubits_left) if i not in randoms]
        keybits = ''.join(str(q[1]) for q in qubits)

        key = int(keybits, 2).to_bytes((len(keybits) + 7) // 8, 'little')
        
        print()
        print('[!] Correctly generated %d safe bits\n' % len(qubits))

    # Here we start acting as a web browser

    print("[+] Sending encrypted request to the web server")

    username = 'GreatUsername'
    password = 'SecurePassword'
    pt = json.dumps({"username": username, "password": password}).encode()

    if CIPHER == 'AES':
        # Create AES key
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(hashlib.sha256(key).digest(), AES.MODE_CBC, iv)
        ct = cipher.encrypt(pad(pt, AES.block_size))
        data = b64encode(iv+ct)
    else:  # use OTP
        ct = bytes([_a ^ _b for _a, _b in zip(pt, itertools.cycle(key))])
        # Given that this is a simulation we cycle the key just not to throw errors, by doing this we are killing OTP security ( if len(key) < len(data) )
        # A fix would be just to increase the qubits, however the CQC backend crashes with 1024+ qubits
        data = b64encode(ct)

    url = "http://127.0.0.1:5000/register"

    time.sleep(2)

    print()

    # Registration request
    requests.post(url, data={'data': data})

    input()
