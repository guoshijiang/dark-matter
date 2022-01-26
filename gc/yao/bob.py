from cryptography.fernet import Fernet
import random
import json


class Gate(object):

    def __init__(self, circuit, g_id, gate_json):
        self.circuit = circuit
        self.g_id = g_id
        self.inputs = {0: gate_json["inputs"]["0"],
                       1: gate_json["inputs"]["1"]}
        self.table = [bytes(bytearray(t["__value__"])) for t in gate_json["table"]]  # the garbled output table

        self.output = None

    def grab_inputs(self):
        return {0: self.circuit.gates[self.inputs[0]].fire(),
                1: self.circuit.gates[self.inputs[1]].fire()}

    def fire(self):
        if self.output is None:
            keys = self.grab_inputs()
            print(self.g_id, keys, self.table)

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
    def __init__(self, circuit, g_id, gate_json):
        Gate.__init__(self, circuit, g_id, gate_json)

    def grab_inputs(self):
        return {0: self.circuit.inputs[self.inputs[0]],
                1: self.circuit.inputs[self.inputs[1]]}


class Circuit(object):
    def __init__(self, circuit_json):
        self.num_inputs = circuit_json["num_inputs"]
        self.gates = {}

        for g_id, g in circuit_json["on_input_gates"].items():
            self.gates[int(g_id)] = OnInputGate(self, g_id, g)

        for g_id, g in circuit_json["gates"].items():
            self.gates[int(g_id)] = Gate(self, g_id, g)

        self.output_gate_ids = circuit_json["output_gate_ids"]

    def fire(self, inputs):
        self.inputs = inputs
        output = {}
        print(self.output_gate_ids)
        print(self.gates)
        for g_id in self.output_gate_ids:
            output[g_id] = self.gates[g_id].fire()
        return output


with open('circuit.json') as data_file:
    data = json.load(data_file)

mycirc = Circuit(data)