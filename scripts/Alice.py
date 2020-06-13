from cqc.pythonLib import CQCConnection, qubit

from werkzeug.security import generate_password_hash

import random, progressbar, time, itertools, sys, json, mysql.connector, os, logging, hashlib
from config import N_QUBITS as N
from config import VERBOSE
from config import ALICE_CLASSICAL_RECIPIENT, ALICE_QUANTUM_RECIPIENT
from config import CIPHER

if CIPHER == 'AES':
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad

from base64 import b64decode

from flask import Flask
from flask import request

if __name__ == '__main__':

    # Initialize CQCConnection as Alice
    with CQCConnection("Alice") as Alice:

        # Generate qubits
        qubits = []
        print("\n[+] Alice: [Generating %d qubits]" % N)
        bar = progressbar.ProgressBar(maxval=N, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        bar.start()
        for i in range(N):
            qubits.append((qubit(Alice),             # qubit
                            random.randint(0, 1),    # bits (Ka)
                            random.randint(0, 1)))   # basis (Ba)
            bar.update(i+1)
        bar.finish()
        print("[+] Alice: [Generated %d qubits]" % N)

        # Encode the qubits in the basis and send them
        print("\n[+] Alice: [Sending %d qubits]" % N)
        bar = progressbar.ProgressBar(maxval=N, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        bar.start()
        for i in range(N):

            if qubits[i][1] == 1:
                qubits[i][0].X()  # Bit flip 0> to 1> (Pauli-X gate)
            if qubits[i][2] == 1:
                qubits[i][0].H()  # Encode in Hadamard basis (Hadamard gate)

            Alice.sendQubit(qubits[i][0], ALICE_QUANTUM_RECIPIENT)

            bar.update(i+1)
        bar.finish()
        print("[+] Alice: [Sent %d qubits]\n" % N)

        # Workaround for async sockets
        time.sleep(1)

        # Receive Bob's basis and filter the invalid basis
        bob_basis = [int(_) for _ in Alice.recvClassical(msg_size=N*4).decode()]

        alice_bases = [qubit[2] for qubit in qubits]

        index_to_discard = [i for i in range(N) if bob_basis[i] != alice_bases[i]]

        print("[+] Received Bob's basis")
        print("[+] Filtering invalid basis")

        # Send invalid basis to Bob
        Alice.sendClassical(ALICE_CLASSICAL_RECIPIENT, b''.join((str(_)+'-').encode() for _ in index_to_discard))
        print('[+] Sending invalid basis to Bob')

        # Discard bits with invalid basis
        qubits = [qubits[i] for i in range(N) if i not in index_to_discard]
        qubits_left = len(qubits)

        # Receive qbits to check for MITM
        to_check = [int(_) for _ in Alice.recvClassical(msg_size=N*4).decode()[:-1].split('-')]
        print("[+] Received Bob's bits\n")

        n = len(to_check) // 2  # how many index or values we have

        # len(to_check) should always be even
        assert(len(to_check) % 2 == 0)

        indexes = []  # list for index of bits to check
        values = []  # list for values of Bob's measurements
        correct = 0  # counter for how many measurements are correct

        v = iter(to_check)  # iterate over the received list
        for i in v:
            indexes.append(i)
            values.append(next(v))

        for i in range(n):  # check if measurements are equals
            if qubits[indexes[i]][1] == values[i]:
                correct += 1

        # check result
        correctness = correct*100//n
        print('[!]', correctness, "% of the received bits are correct")

        if correctness < 99:
            Alice.sendClassical(ALICE_CLASSICAL_RECIPIENT, b"abort")
            print('[!!] Looks like someone is intercepting our traffic, abort now...')
            input()
        else:
            Alice.sendClassical(ALICE_CLASSICAL_RECIPIENT, b"all good")

        print('[+] We can proceed, sending confirm to Bob')
        qubits = [qubits[i] for i in range(qubits_left) if i not in indexes]
        keybits = ''.join(str(q[1]) for q in qubits)

        key = int(keybits, 2).to_bytes((len(keybits) + 7) // 8, 'little')

        print()
        print('[!] Correctly generated %d safe bits\n' % len(qubits))

    # # Here we start acting as a web server
    app = Flask(__name__)

    # disable flask verbosity
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    os.environ['WERKZEUG_RUN_MAIN'] = 'true'

    @app.route('/register', methods=['POST'])
    def register():
        if request.method == 'POST':
            data = request.form.to_dict()['data']

            print('[x] Encrypted data received: ', data)

            data = b64decode(data)

            print('[+] Decrypting using ', CIPHER)

            if CIPHER == 'AES':
                iv = data[:16]  # extract IV
                ct = data[16:]  # extract Ciphertext
                cipher = AES.new(hashlib.sha256(key).digest(), AES.MODE_CBC, iv)  # create the AES cipher
                pt = unpad(cipher.decrypt(ct), AES.block_size).decode() # decrypt the ciphertext and unpad it
            else:  # use OTP
                pt = bytes([_a ^ _b for _a, _b in zip(data, itertools.cycle(key))]).decode()
                # Given that this is a simulation we cycle the key just not to throw errors, by doing this we are killing OTP security ( if len(key) < len(data) )
                # A fix would be just to increase the qubits, however the CQC backend crashes with 1024+ qubits
            form = json.loads(pt)

            print('[x] Decrypted data: ', pt, '\n')

            # MySQL DATABASE
            try:
                conn = mysql.connector.connect(host="localhost", user="tesina", database="progetto_tesina")
                cur = conn.cursor(prepared=True)

                query = "INSERT INTO users (username, password) VALUES (%s, %s)"

                username = conn._cmysql.escape_string(form['username']) # if mysql-connector is installed instead of mysql-connector-python this will fail
                password = generate_password_hash(form['password'])

                cur.execute(query, (username, password))
                conn.commit()
            except mysql.connector.Error as error:
                print("Query failed {}".format(error))
            finally:
                if (conn.is_connected()):
                    cur.close()
                    conn.close()

            print('[+] Utente registrato')

        return 'done'

    print('[+] Starting Flask web server\n')
    app.run()

    input()
