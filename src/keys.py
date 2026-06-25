import os
import hashlib
import hmac
import json
import arweave

#Shared functions

#Advanced ratchet mechanism
def advance_ratchet(k_ratchet):
    return hmac.new(k_ratchet, b"RATCHET", hashlib.sha256).digest()

#Derives our per task keys
def derive_cmd_key(k_ratchet, salt):
    return hmac.new(k_ratchet, salt + b"CMDKEY", hashlib.sha256).digest()


#Server side functions

def server_generate_k_root():
    K_root = os.urandom(32)
    return K_root

def server_derive_allkeys(K_root):
    server_keys = {}

    #Derives K_ratchet
    K_ratchet = hmac.new(K_root, b"RATCHET_INIT", hashlib.sha256).digest()
    server_keys["K_ratchet"] = K_ratchet

    #Derives K_exfil_ratchet
    K_exfil_ratchet  = hmac.new(K_root, b"EXFIL_RATCHET_INIT", hashlib.sha256).digest()
    server_keys["K_exfil_ratchet"] = K_exfil_ratchet

    #Derives K_extract
    K_extract = hmac.new(K_root, b"EXTRACT", hashlib.sha256).digest()
    server_keys["K_extract"] = K_extract

    return server_keys

#Saves K_root to keyfile.
def server_save_server_keys(keyfile_path, k_root):
    server_keys = {"K_root": k_root.hex()}

    with open(keyfile_path, "w") as f:
        json.dump(server_keys, f)

#Loads K_root from keyfile
def server_load_server_keys(keyfile_path):
    #Opens keyfile
    try: 
        with open(keyfile_path, "r") as f:
            data = json.load(f)
            return bytes.fromhex(data["K_root"])
    #If keyfile doesnt exist
    except FileNotFoundError:
        server_key = server_generate_k_root()
        server_save_server_keys(keyfile_path, server_key)
        return server_key


#Agent side functions

def agent_save_agent_keys(keyfile_path, K_ratchet, K_exfil_ratchet, K_extract):
    print("ABC")

def agent_load_agent_keys(keyfile_path):
    print("ABC")


#Wallet functions

def load_wallet(keyfile_path):
    print("ABC")




