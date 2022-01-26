#!/usr/bin/env python3
import logging
import ot
import util
import yao
from abc import ABC, abstractmethod


logging.basicConfig(format="[%(levelname)s] %(message)s",level=logging.WARNING)


"""Yao 乱码的抽象类（例如 Alice)"""
class YaoGarbler(ABC):
    def __init__(self, circuits):
        circuits = util.parse_json(circuits)
        self.name = circuits["name"]
        self.circuits = []
        for circuit in circuits["circuits"]:
            garbled_circuit = yao.GarbledCircuit(circuit)
            pbits = garbled_circuit.get_pbits()
            entry = {
                "circuit": circuit,
                "garbled_circuit": garbled_circuit,
                "garbled_tables": garbled_circuit.get_garbled_tables(),
                "keys": garbled_circuit.get_keys(),
                "pbits": pbits,
                "pbits_out": {w: pbits[w] for w in circuit["out"]},
            }
            self.circuits.append(entry)

    @abstractmethod
    def start(self):
        pass


class Alice(YaoGarbler):
    """
    Alice是 Yao 电路的创造者。
      Alice 创建了一个 Yao 电路并将其与她的加密输入一起发送给评估器。 Alice 最终会打印出电路的真值表
      对于 Alice->Bob 输入的所有组合。
      Alice 不知道 Bob 的输入，但出于此目的
      仅打印真值表，Alice 假设 Bob 的输入如下一个特定的命令
      Attributes：
        circuits：包含电路的 JSON 文件
        oblivious_transfer：可选;启用不经意传输协议(默认为真0。
    """
    def __init__(self, circuits, oblivious_transfer=True):
        super().__init__(circuits)
        self.socket = util.GarblerSocket()
        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)

    def start(self):
        """开启 Yao 协议."""
        for circuit in self.circuits:
            to_send = {
                "circuit": circuit["circuit"],
                "garbled_tables": circuit["garbled_tables"],
                "pbits_out": circuit["pbits_out"],
            }
            logging.debug(f"Sending {circuit['circuit']['id']}")
            self.socket.send_wait(to_send)
            self.print(circuit)

    def print(self, entry):
        """打印所有 Bob 和 Alice 输入的电路评估
        参数:
            entry: 要评估的电路的字典.
        """
        circuit, pbits, keys = entry["circuit"], entry["pbits"], entry["keys"]
        outputs = circuit["out"]
        a_wires = circuit.get("alice", [])  # Alice 的线路
        a_inputs = {}  # 从 Alice 的线路映射到 (key, encr_bit) 输入
        b_wires = circuit.get("bob", [])  # Bob 的线路
        b_keys = {  # 从 Bob 的电线映射到一对 (key, encr_bit)
            w: self._get_encr_bits(pbits[w], key0, key1)
            for w, (key0, key1) in keys.items() if w in b_wires
        }
        N = len(a_wires) + len(b_wires)
        print(f"======== {circuit['id']} ========")
        # 为 Alice 和 Bob 生成所有输入
        for bits in [format(n, 'b').zfill(N) for n in range(2**N)]:
            bits_a = [int(b) for b in bits[:len(a_wires)]]  # Alice 的输入
            # 将 Alice 的线路映射到 (key, encr_bit)
            for i in range(len(a_wires)):
                a_inputs[a_wires[i]] = (keys[a_wires[i]][bits_a[i]],
                                        pbits[a_wires[i]] ^ bits_a[i])
            # 将 Alice 的加密输入和密钥发送给 Bob
            result = self.ot.get_result(a_inputs, b_keys)
            # 格式化输出
            str_bits_a = ' '.join(bits[:len(a_wires)])
            str_bits_b = ' '.join(bits[len(a_wires):])
            str_result = ' '.join([str(result[w]) for w in outputs])
            print(f"  Alice{a_wires} = {str_bits_a} "
                  f"Bob{b_wires} = {str_bits_b}  "
                  f"Outputs{outputs} = {str_result}")
        print()

    def _get_encr_bits(self, pbit, key0, key1):
        return ((key0, 0 ^ pbit), (key1, 1 ^ pbit))


class Bob:
    """Bob 是 Yao 电路的接收者和评估者.
    Bob 从 Alice 接收 Yao 电路，计算结果并发送他们回去.
    Args:
       oblivious_transfer：可选;启用不经意传输协议(默认为真0。
    """
    def __init__(self, oblivious_transfer=True):
        self.socket = util.EvaluatorSocket()
        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)

    def listen(self):
        """开始监听 Alice 的消息."""
        logging.info("Start listening")
        try:
            for entry in self.socket.poll_socket():
                self.socket.send(True)
                self.send_evaluation(entry)
        except KeyboardInterrupt:
            logging.info("Stop listening")

    def send_evaluation(self, entry):
        """评估所有 Bob 和 Alice 的输入的 yao 电路发送回结果.
        参数:
            entry: 表示要评估的电路的字典。
        """
        circuit, pbits_out = entry["circuit"], entry["pbits_out"]
        garbled_tables = entry["garbled_tables"]
        a_wires = circuit.get("alice", [])  # 列出 Alice 的线路
        b_wires = circuit.get("bob", [])  # 列出 Bob 的线路
        N = len(a_wires) + len(b_wires)

        print(f"Received {circuit['id']}")

        # 为 Alice 和 Bob 生成所有可能的输入
        for bits in [format(n, 'b').zfill(N) for n in range(2**N)]:
            bits_b = [int(b) for b in bits[N - len(b_wires):]]  # Bob 的输入
            # 创建 dict 将 Bob 的每一根线映射到 Bob 的输入
            b_inputs_clear = {
                b_wires[i]: bits_b[i]
                for i in range(len(b_wires))
            }
            # 评估并将结果发送给 Alice
            self.ot.send_result(circuit, garbled_tables, pbits_out, b_inputs_clear)


class LocalTest(YaoGarbler):
    """一个本地测试类.
    打印电路评估或乱码表。
    参数:
        circuits: 包含电路的 JSON 文件
        print_mode: 打印乱码表格的清晰版本或电路评估（默认）
    """
    def __init__(self, circuits, print_mode="circuit"):
        super().__init__(circuits)
        self._print_mode = print_mode
        self.modes = {
            "circuit": self._print_evaluation,
            "table": self._print_tables,
        }
        logging.info(f"Print mode: {print_mode}")

    def start(self):
        """开启本地 Yao 协议"""
        for circuit in self.circuits:
            self.modes[self.print_mode](circuit)

    def _print_tables(self, entry):
        """打印电路表"""
        entry["garbled_circuit"].print_garbled_tables()

    def _print_evaluation(self, entry):
        """打印电路评估值."""
        circuit, pbits, keys = entry["circuit"], entry["pbits"], entry["keys"]
        garbled_tables = entry["garbled_tables"]
        outputs = circuit["out"]
        a_wires = circuit.get("alice", [])  # Alice 的线路
        a_inputs = {}  # 从 Alice 的线路映射到 (key, encr_bit) 输入
        b_wires = circuit.get("bob", [])  # Bob 的线路
        b_inputs = {}  # 从 Bob 的电线映射到 (key, encr_bit) 输入
        pbits_out = {w: pbits[w] for w in outputs}  # p-bits 输出
        N = len(a_wires) + len(b_wires)
        print(f"======== {circuit['id']} ========")
        # 为 Alice 和 Bob 生成所有可能的输入
        for bits in [format(n, 'b').zfill(N) for n in range(2**N)]:
            bits_a = [int(b) for b in bits[:len(a_wires)]]  # Alice's inputs
            bits_b = [int(b) for b in bits[N - len(b_wires):]]  # Bob's inputs
            # 将 Alice 的线路映射到 (key, encr_bit)
            for i in range(len(a_wires)):
                a_inputs[a_wires[i]] = (
                    keys[a_wires[i]][bits_a[i]],
                    pbits[a_wires[i]] ^ bits_a[i]
                )

            # 将 Bob 的电线映射到 (key, encr_bit)
            for i in range(len(b_wires)):
                b_inputs[b_wires[i]] = (
                    keys[b_wires[i]][bits_b[i]],
                    pbits[b_wires[i]] ^ bits_b[i]
                )
            result = yao.evaluate(circuit, garbled_tables, pbits_out, a_inputs, b_inputs)
            # 格式化输出
            str_bits_a = ' '.join(bits[:len(a_wires)])
            str_bits_b = ' '.join(bits[len(a_wires):])
            str_result = ' '.join([str(result[w]) for w in outputs])
            print(f"  Alice{a_wires} = {str_bits_a} "
                  f"Bob{b_wires} = {str_bits_b}  "
                  f"Outputs{outputs} = {str_result}")
        print()

    @property
    def print_mode(self):
        return self._print_mode

    @print_mode.setter
    def print_mode(self, print_mode):
        if print_mode not in self.modes:
            logging.error(f"Unknown print mode '{print_mode}', "
                          f"must be in {list(self.modes.keys())}")
            return
        self._print_mode = print_mode


def main(
    party,
    circuit_path="circuits/default.json",
    oblivious_transfer=True,
    print_mode="circuit",
    loglevel=logging.WARNING,
):
    logging.getLogger().setLevel(loglevel)
    if party == "alice":
        alice = Alice(circuit_path, oblivious_transfer=oblivious_transfer)
        alice.start()
    elif party == "bob":
        bob = Bob(oblivious_transfer=oblivious_transfer)
        bob.listen()
    elif party == "local":
        local = LocalTest(circuit_path, print_mode=print_mode)
        local.start()
    else:
        logging.error(f"Unknown party '{party}'")


if __name__ == '__main__':
    import argparse
    def init():
        loglevels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        parser = argparse.ArgumentParser(description="Run Yao protocol.")
        parser.add_argument(
            "party",
            choices=["alice", "bob", "local"],
            help="the yao2mpc party to run"
        )

        parser.add_argument(
            "-c",
            "--circuit",
            metavar="circuit.json",
            default="circuits/default.json",
            help=("the JSON circuit file for alice and local tests"),
        )

        parser.add_argument(
            "--no-oblivious-transfer",
            action="store_true",
            help="disable oblivious transfer"
        )

        parser.add_argument(
            "-m",
            metavar="mode",
            choices=["circuit", "table"],
            default="circuit",
            help="the print mode for local tests (default 'circuit')"
        )

        parser.add_argument(
            "-l",
            "--loglevel",
            metavar="level",
            choices=loglevels.keys(),
            default="warning",
            help="the log level (default 'warning')"
        )

        main(
            party=parser.parse_args().party,
            circuit_path=parser.parse_args().circuit,
            oblivious_transfer=not parser.parse_args().no_oblivious_transfer,
            print_mode=parser.parse_args().m,
            loglevel=loglevels[parser.parse_args().loglevel],
        )
    init()
