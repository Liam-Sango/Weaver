import sys
import struct

OPCODE_TABLE = {
    # Stack
    "PUSH32": 0x01,
    "DUP": 0x02,
    "SWAP": 0x03,
    "DROP": 0x04,

    # Arithmetic
    "ADD": 0x10,
    "SUB": 0x11,
    "AND": 0x12,
    "OR": 0x13,
    "XOR": 0x14,
    "NOT": 0x15,

    # Memory
    "LOAD32": 0x20,
    "STORE32": 0x21,

    # Control
    "JMP": 0x30,
    "JZ": 0x31,
    "JNZ": 0x32,
    "CALL": 0x33,
    "RET": 0x34,

    # System
    "SYSCALL": 0x40,

    # Halt
    "HALT": 0xFF,
}


def parsed_bytecode_line(instruction):
    parsed_bytecode_line = b""

    #Opcode checking
    instruction_list = instruction.split(" ", 1)

    if instruction_list[0] not in OPCODE_TABLE:
        raise ValueError("parsed Opcode mmemoric in parse_btyecode_line is not present in instruction table")
    
    instruction_mnemonic = instruction_list[0] 
    opcode_byte = OPCODE_TABLE[instruction_mnemonic]
    
    if (len(instruction_list) == 2):
         instruction_operand = instruction_list[1] 
    else:
        instruction_operand = None


    SINGLE_BYTE_OPS = {"DUP", "SWAP", "DROP", "ADD", "SUB", "AND", "OR", "XOR", "NOT", "LOAD32", "STORE32", "RET", "HALT"}
    TWO_BYTE_OPS = {"JMP", "JZ", "JNZ", "CALL"}

    if (instruction_operand is not None and instruction_mnemonic in SINGLE_BYTE_OPS): 
        raise ValueError("Parsed invalid instruction operand pairing in parsed_bytecode_line,") 
    
    #Single byte operations
    elif (instruction_mnemonic in SINGLE_BYTE_OPS):
        parsed_bytecode_line = bytes([opcode_byte])

    #Two byte operations
    elif (instruction_mnemonic in TWO_BYTE_OPS):

        if(instruction_operand is None):
            raise ValueError("Parsed invalid instruction operand pairing in parsed_bytecode_line,") 
        
        int_value = int(instruction_operand)
        packed_bytes = struct.pack(">h", int_value)

        parsed_bytecode_line = bytes([opcode_byte]) + packed_bytes

    #Push32
    elif (instruction_mnemonic == "PUSH32"):

        if(instruction_operand is None):
            raise ValueError("Parsed invalid instruction operand pairing in parsed_bytecode_line,") 
        
        int_value = int(instruction_operand)
        packed_bytes = struct.pack(">i", int_value)

        parsed_bytecode_line = bytes([opcode_byte]) + packed_bytes

    elif (instruction_mnemonic == "SYSCALL"):

        if(instruction_operand is None):
            raise ValueError("Parsed invalid instruction operand pairing in parsed_bytecode_line,") 
        
        int_value = int(instruction_operand)
        packed_bytes = struct.pack(">B", int_value)

        parsed_bytecode_line = bytes([opcode_byte]) + packed_bytes
      


    #Second pass (Labels)
    return parsed_bytecode_line
    

def assemble_payload(bytecode):
    payload = ""

    if sys.getsizeof(payload > 256):
        return 0
    

    print("")

