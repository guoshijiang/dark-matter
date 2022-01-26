from hashlib import sha512

class Gate:
    def __init__(self, circuit, type, gate_id, inputs):
        self.circuit = circuit
        self.type = type
        self.gate_id = gate_id
        self.inputs = inputs
        self.output = None

    def fire(self):
        if self.type != "INP":
            input0 = self.circuit.get(self.inputs[0]).fire()
            if self.type != "NOT":
                input1 = self.circuit.get(self.inputs[1]).fire()

        if self.output is None:
            if self.type == "AND":
                self.output = input0 and input1
            elif self.type == "OR":
                self.output = input1 or input0
            elif self.type == "XOR":
                self.output = input0 ^ input1
            elif self.type == "NOT":
                self.output = 1 - input0
            elif self.type == "INP":
                self.output = self.circuit.inputs[self.gate_id]
            else:
                print("bad gate type")

        return self.output

    def reset(self):
        self.output = None

class Circuit:
    def __init__(self, num_inputs, num_outputs):
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self.gates = {}
        self.gateids = []
        self.output_gateids = []

        for gate_id in range(num_inputs):
            self.gateids.append(gate_id)
            new_gate = Gate(self, "INP", gate_id, [])
            self.gates[gate_id] = new_gate


    def get(self, gate_id):
        return self.gates[gate_id]

    def add_gate(self, type, inputs):
        new_id = self.gateids[-1] + 1
        if (new_id) not in self.gateids:
            self.gateids.append(new_id)
            new_gate = Gate(self, type, new_id, inputs)
            self.gates[new_id] = new_gate
            return new_id
        else:
            print("Error with creating gate id")

    def make_ouput_gate(self, gate_id):
        if gate_id in self.gateids:
            self.output_gateids.append(gate_id)
        else:
            print("Gate id not found")

    def fire(self, inputs):
        if len(inputs) != self.num_inputs:
            print("Incorrect amount of inputs")
        else:
            self.inputs = inputs
        gate_output = {}
        for gate_id in self.output_gateids:
            gate_output[gate_id] = self.get(gate_id).fire()
        self.reset()
        return gate_output

    def reset(self):
        for i, gate  in self.gates.items():
            gate.reset()


class GCircuit(object):
    """docstring for GCircuit"""
    def __init__(self, circuit):
        self.circuit = circuit
        self.generate_gcircuit(circuit)

    def generate_gcircuit(circuit):
        pass

num = 2**13
m = num

circ = Circuit(m,1)

m = m//2

count = 0

while m != 1:
    for i in range(m):
        circ.add_gate("OR", [count+i*2, count+i*2+1])

    count += m
    print(m)
    print(len(circ.gates))
    m = m//2

circ.make_ouput_gate(len(circ.gates)-1)

out = circ.fire([x%2 for x in range(num - 1)] + [0])
print(out)