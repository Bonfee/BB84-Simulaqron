from cqc.pythonLib import CQCConnection, qubit

import random
from config import N_QUBITS as N
from config import EVE_IS_INTERFERING

if __name__ == '__main__':

    # Initialize CQCConnection as Eve
    with CQCConnection("Eve") as Eve:
        
        if EVE_IS_INTERFERING:
            print('[+] Intercepting and measuring qubits...')
        else:
            print('[+] Intercepting qubits...')

        for i in range(N):
            qbittt = Eve.recvQubit()

            if EVE_IS_INTERFERING:
                # Choose random basis to measure the qubit in
                base = random.randint(0,1)

                # Hadamard gate
                if base == 1:
                    qbittt.H()

                qbittt.measure(inplace=True)

            Eve.sendQubit(qbittt, "Bob")

    input()