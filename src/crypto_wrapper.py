import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from src.keys import derive_cmd_key, advance_ratchet

#Replaces a key with zero.
def zero_key (key: bytearray):
    for x in range(len(key)):
        key[x] = 0

def encrypt_task(bytecode: bytes, K_ratchet: bytes) -> tuple[bytes, bytes]:
    #Gets random values
    salt = os.urandom(16)
    iv = os.urandom(12)

    #Derives K_cmd
    k_cmd = bytearray(derive_cmd_key(K_ratchet, salt))

    #Encrypts and returns bytecode
    aesgcm = AESGCM(bytes(k_cmd))
    ciphertext_and_tag = aesgcm.encrypt(iv, bytecode, None)
    payload = salt + iv + ciphertext_and_tag

    zero_key(k_cmd)
    new_k_ratchet = advance_ratchet(K_ratchet)
    return(payload, new_k_ratchet)

def decrypt_task(payload: bytes, K_ratchet: bytes) -> tuple[bytes, bytes] | None:
    #Reject payloads too short to contain salt + IV + tag
    if len(payload) < 28 + 16:
        return None

    #Gets random values
    salt = payload[0:16]
    iv = payload[16:28]
    ciphertext_and_tag = payload[28:]

    #Derives K_cmd
    k_cmd = bytearray(derive_cmd_key(K_ratchet, salt))
    aesgcm = AESGCM(bytes(k_cmd))

    #Decrypts and returns plaintext bytecode
    try:
        plaintext_bytecode = aesgcm.decrypt(iv, ciphertext_and_tag, None)
    except InvalidTag:
        zero_key(k_cmd)
        return None
    else:
        zero_key(k_cmd)
        new_k_ratchet = advance_ratchet(K_ratchet)
        return plaintext_bytecode, new_k_ratchet

