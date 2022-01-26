import hashlib
import logging
import pickle
import util
import yao


class ObliviousTransfer:
    def __init__(self, socket, enabled=True):
        self.socket = socket
        self.enabled = enabled

    def get_result(self, a_inputs, b_keys):
        """发送 Alice 的输入并检索 Bob 的评估结果.
        参数:
            a_inputs: 将 Alice 的电线映射到 (key, encr_bit) 输入的字典。
            b_keys: 将每个 Bob 的线映射到一对 (key, encr_bit) 的字典。
        返回值:
            yao 电路评测结果。
        """
        logging.debug("Sending inputs to Bob")
        self.socket.send(a_inputs)

        for _ in range(len(b_keys)):
            w = self.socket.receive()  # 接收门 ID 在哪里执行 OT
            logging.debug(f"Received gate ID {w}")

            if self.enabled:  # 执行不经意传输
                pair = (pickle.dumps(b_keys[w][0]), pickle.dumps(b_keys[w][1]))
                self.ot_garbler(pair)
            else:
                to_send = (b_keys[w][0], b_keys[w][1])
                self.socket.send(to_send)

        return self.socket.receive()

    def send_result(self, circuit, g_tables, pbits_out, b_inputs):
        """评估电路并且发送结果给 Alice.
        Args:
            circuit: 包含电路规范的字典.
            g_tables: yao 电路乱码表.
            pbits_out: p 位输出.
            b_inputs: 将 Bob 的线路映射到（清除）输入位的 dict.
        """
        a_inputs = self.socket.receive()
        b_inputs_encr = {}
        logging.debug("Received Alice's inputs")
        for w, b_input in b_inputs.items():
            logging.debug(f"Sending gate ID {w}")
            self.socket.send(w)
            if self.enabled:
                b_inputs_encr[w] = pickle.loads(self.ot_evaluator(b_input))
            else:
                pair = self.socket.receive()
                logging.debug(f"Received key pair, key {b_input} selected")
                b_inputs_encr[w] = pair[b_input]
        result = yao.evaluate(circuit, g_tables, pbits_out, a_inputs, b_inputs_encr)
        logging.debug("Sending circuit evaluation")
        self.socket.send(result)

    def ot_garbler(self, msgs):
        """不经意的转换, 和 alice 相关.
        参数:
            msgs: 建议给 Bob 的一对消息 (msg1, msg2).
        """
        logging.debug("OT protocol started")
        G = util.PrimeGroup()
        self.socket.send_wait(G)
        c = G.gen_pow(G.rand_int())
        h0 = self.socket.send_wait(c)
        h1 = G.mul(c, G.inv(h0))
        k = G.rand_int()
        c1 = G.gen_pow(k)
        e0 = util.xor_bytes(msgs[0], self.ot_hash(G.pow(h0, k), len(msgs[0])))
        e1 = util.xor_bytes(msgs[1], self.ot_hash(G.pow(h1, k), len(msgs[1])))
        self.socket.send((c1, e0, e1))
        logging.debug("OT protocol ended")

    def ot_evaluator(self, b):
        """不经意的转换，和 bob 相关.
        参数:
            b: Bob 的输入位用于选择 Alice 的一条消息.
        返回值:
            Bob 选择的消息。
        """
        logging.debug("OT protocol started")
        G = self.socket.receive()
        self.socket.send(True)
        # 基于 Nigel Smart 的“密码学变得简单”的 OT 协议
        c = self.socket.receive()
        x = G.rand_int()
        x_pow = G.gen_pow(x)
        h = (x_pow, G.mul(c, G.inv(x_pow)))
        c1, e0, e1 = self.socket.send_wait(h[b])
        e = (e0, e1)
        ot_hash = self.ot_hash(G.pow(c1, x), len(e[b]))
        mb = util.xor_bytes(e[b], ot_hash)
        logging.debug("OT protocol ended")
        return mb

    @staticmethod
    def ot_hash(pub_key, msg_length):
        """OT 密钥的哈希函数"""
        key_length = (pub_key.bit_length() + 7) // 8  # Byte 的长度
        bytes = pub_key.to_bytes(key_length, byteorder="big")
        return hashlib.shake_256(bytes).digest(msg_length)
