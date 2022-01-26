import struct
import base64
import binascii
from Crypto.Cipher import AES


MAGIC = "AFB9D3C8"
KEY = "yBgjAGO7ZWFfANlE0dU9"

BLOCK_SIZE = 32
PADDING = '{'
DELIMITER = '|'
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
EncodeAES = lambda p, s: base64.b64encode(AES.new(pad(p)).encrypt(pad(s)))
DecodeAES = lambda p, e: AES.new(pad(p)).decrypt(base64.b64decode(e)).rstrip(PADDING)
encode_tx = lambda tx: base64.b64encode(binascii.a2b_hex(tx))
decode_tx = lambda tx: binascii.b2a_hex(base64.b64decode(tx))

if __name__ == '__main__':
    message = "aaaaaaaa"
    secret_msg = EncodeAES("1117", message)
    print("secret_msg==", secret_msg)
    d_message = DecodeAES("1117", secret_msg)
    print("d_message==", d_message)
