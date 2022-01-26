from cryptography.fernet import Fernet
from random import SystemRandom
from profilehooks import profile

cryptorand = SystemRandom()


def shuffle(l):
    for i in range(len(l) - 1, 0, -1):
        j = cryptorand.randrange(i + 1)
        l[i], l[j] = l[j], l[i]


def keypair():
    return [Fernet.generate_key(), Fernet.generate_key()]


class Gate(object):

    def keypair(self):
        return keypair()

    def grab_wires(self):
        return [self.circuit.gates[x].outputs for x in self.inputs]

    gate_ref = {
        "AND": (lambda x, y: x and y),
        "XOR": (lambda x, y: x ^ y),
        "OR": (lambda x, y: x or y)
    }

    def __init__(self, circuit, g_id, ctype, inputs):
        self.circuit = circuit
        self.g_id = g_id
        self.inputs = inputs
        self.outputs = self.keypair()
        # array of keys for output, [false, true]
        self.table = []  # the garbled output table

        wires = self.grab_wires()

        self.output = None

        f = [[Fernet(key) for key in wire] for wire in wires]

        for i in range(2):
            for j in range(2):
                if self.gate_ref[ctype](i, j):
                    enc = f[0][i].encrypt(self.outputs[1])
                    self.table.append(f[1][j].encrypt(enc))
                else:
                    enc = f[0][i].encrypt(self.outputs[0])
                    self.table.append(f[1][j].encrypt(enc))

        shuffle(self.table)

    def grab_inputs(self):
        return [self.circuit.gates[g].fire() for g in self.inputs]

    def fire(self):
        if self.output is None:
            keys = self.grab_inputs()

            fs = [Fernet(keys[1]), Fernet(keys[0])]

            decrypt_table = self.table
            for f in fs:
                new_table = []
                for ciphertext in decrypt_table:
                    dec = None
                    try:
                        dec = f.decrypt(ciphertext)
                    except:
                        pass
                    if dec is not None:
                        new_table.append(dec)
                decrypt_table = new_table

            if len(decrypt_table) != 1:
                raise ValueError("decrypt_table should be length 1 after decrypting")

            self.output = decrypt_table[0]

        return self.output


class OnInputGate(Gate):
    def grab_wires(self):
        return [self.circuit.poss_inputs[x] for x in self.inputs]

    def __init__(self, circuit, g_id, ctype, inputs):
        Gate.__init__(self, circuit, g_id, ctype, inputs)

    def grab_inputs(self):
        return [self.circuit.inputs[i] for i in self.inputs]


class OutputGate(Gate):
    def keypair(self):
        return [bytes([0]), bytes([1])]

    def __init__(self, circuit, g_id, ctype, inputs):
        Gate.__init__(self, circuit, g_id, ctype, inputs)


class Circuit(object):
    def __init__(self, num_inputs, on_input_gates, mid_gates, output_gates):
        self.poss_inputs = [keypair() for x in range(num_inputs)]
        self.gates = {}

        for g in on_input_gates:
            self.gates[g[0]] = OnInputGate(self, g[0], g[1], g[2])

        for g in mid_gates:
            self.gates[g[0]] = Gate(self, g[0], g[1], g[2])

        self.output_gate_ids = []
        for g in output_gates:
            self.output_gate_ids.append(g[0])
            self.gates[g[0]] = OutputGate(self, g[0], g[1], g[2])

    @profile
    def fire(self, inputs):
        self.inputs = inputs
        output = {}
        for g_id in self.output_gate_ids:
            output[g_id] = self.gates[g_id].fire()
        return output


num_inputs = 2 ** 12

"""
on_input_gates = [[0, "AND", [0, 1]], 
                [1, "XOR", [2, 3]], 
                [2, "OR", [0,3]]]
mid_gates = [[3, "XOR", [0, 1]],
             [4, "OR", [1, 2]]]
output_gates = [[5, "OR", [3, 4]]]
"""

on_input_gates = [[n, "AND", [n * 2, n * 2 + 1]] for n in range(num_inputs // 2)]
mid_gates = []


def make_adder(w0, w1, g_ids):
    gates = [[g_ids[0], "AND", [w0, w1]]
             [g_ids[1], "XOR", [w0, w1]]]

    return gates


def make_gen_adder(wires0, wires1, g_ids):
    gates = []
    for i in range(len(wires0)):
        gates.append(make_adder(wires0[i], wires1[i], g_ids[i]))
    return gates


def make_voting_circuit(num_candidates, num_voters):
    gates = []
    bits_for_cand = ceil(log(num_candidates, 2))
    bits_for_votr = ceil(log(num_voters, 2))


count = num_inputs // 2
m = num_inputs // 4

while m != 1:
    mid_gates.extend([[n + count, "AND", [count - m * 2 + n * 2, count - m * 2 + n * 2 + 1]] for n in range(m)])
    count += m
    m = m // 2

output_gates = [[count, "AND", [count - 2, count - 1]]]

mycirc = Circuit(num_inputs, on_input_gates, mid_gates, output_gates)

my_inputs = [1 for x in range(num_inputs)]
my_enc_inputs = [mycirc.poss_inputs[x][my_inputs[x]] for x in range(num_inputs)]

out = mycirc.fire(my_enc_inputs)

print(out)