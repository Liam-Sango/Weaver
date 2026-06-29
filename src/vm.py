import struct
import logging
import time
import gc
import requests

logger = logging.getLogger(__name__)

#Logs syscall function calls and their return values
def log_function_call(func):
    def wrapper(*args, **kwargs):
        logger.info(f'Calling {func.__name__} with args: {args}, kwargs: {kwargs}')
        result = func(*args, **kwargs)
        logger.info(f'{func.__name__} returned: {result}')
        return result
    return wrapper

#Syscall functions

#Reads a file and pushes it into the VM buffer
@log_function_call
def file_read(vm):
    address = vm.data_stack.pop()

    try:
        path = vm.read_string(address)

        with open(path, "rb") as f:
            data = f.read()

        handle = vm.store_buffer(data)
        return handle

    except FileNotFoundError:
        return -1

    except OSError:
        return -1


@log_function_call
def file_write(vm):
    length = vm.data_stack.pop()
    address = vm.data_stack.pop()
    return 0

#Network handling
@log_function_call
def tcp_connect(vm):
    port = vm.data_stack.pop()
    host_addr = vm.data_stack.pop()
    return 0

@log_function_call
def dns_lookup(vm):
    hostname_addr = vm.data_stack.pop()
    return 0

#Stops VM operation for an amount of time using time.sleep
@log_function_call
def sleep(vm):
    milliseconds = vm.data_stack.pop()

    if milliseconds < 0:
        raise ValueError("Milliseconds should be a positive value.")

    time.sleep(milliseconds / 1000)
    return 0

#Sends a HTTP requests and returns a handle containing the response
@log_function_call
def http_get(vm):
    url_addr = vm.data_stack.pop()

    try:
        url = vm.read_string(url_addr)

        with requests.get(url, timeout=30) as request:
            response = request.content

        handle = vm.store_buffer(response)
        return handle
    
    except requests.exceptions.RequestException:
        return -1
    

@log_function_call
def arweave_upload(vm):
    return 0


#Syscall table
sys_call_table = {
    #File handling
    0: file_read,
    1: file_write,

    #Network handling
    2: tcp_connect,
    3: dns_lookup,
    4: sleep,
    5: http_get,
}

class VirtualMachine:

    def __init__(self, bytecode, memory_size=4096, time_limit=5):

        if not isinstance(memory_size, int):
            raise ValueError("Memory size must be an integer")

        if not isinstance(bytecode, (bytes, bytearray)):
            raise ValueError("Bytecode must be bytes or bytearray")

        if len(bytecode) > 256:
            raise ValueError("Bytecode must be smaller than 256 bytes")

        if memory_size <= 0:
            raise ValueError("Memory size must be above 0")

        self.bytecode = bytearray(bytecode)
        self.data_stack = []
        self.return_stack = []
        self.memory = bytearray(memory_size)
        self.instruction_pointer = 0
        self.is_halted = False
        self.time_limit = time_limit
        self.buffers = {}     
        self.next_handle = 0   

    #creates and stores data in the current handle buffer
    def store_buffer(self, data):
        handle = self.next_handle
        self.buffers[handle] = data
        self.next_handle += 1

        return handle

    #Retrieves data stored in handle buffer,
    def get_buffer(self, handle):
        if handle not in self.buffers:
            raise KeyError("Handle is not in self.buffers.")
    
        return self.buffers[handle]
        
    #reads and decodes a null terminated string from VM memory
    def read_string(self, address):
         if address >= len(self.memory):
             raise ValueError("Address must be smaller than self.memory.")
         
         mem_end = self.memory.find(b'\0', address)
         string = self.memory[address:mem_end].decode('utf-8') if mem_end != -1 else self.memory[address:].decode('utf-8')

         return string

    #Securely zeroes and clears all ephemeral VM state
    def wipe(self):

        #Wipe the data stack
        for x in range(len(self.data_stack)):
            self.data_stack[x] = 0

        #Wipe the return stack
        for x in range(len(self.return_stack)):
            self.return_stack[x] = 0

        #Wipe the VM memory
        for x in range(len(self.memory)):
            self.memory[x] = 0

        #Wipe the bytecode buffer
        for x in range(len(self.bytecode)):
            self.bytecode[x] = 0

        #Final clear of all variables
        self.data_stack.clear()
        self.return_stack.clear()
        self.memory.clear()
        self.bytecode.clear()

        #Run the garbage collector
        gc.collect()

    #Fetch-decode-execute loop with timeout enforcement
    def run(self, time_limit=None):

        if time_limit is None:
            time_limit = self.time_limit

        self.start_time = time.monotonic()
        while not self.is_halted and self.instruction_pointer < len(self.bytecode):

            #Execution
            opcode = self.bytecode[self.instruction_pointer]
            instruction_start = self.instruction_pointer
            self.instruction_pointer += 1

            #Timekeeping
            elapsed_time = time.monotonic()
            if elapsed_time >= self.start_time + time_limit:
                self.is_halted = True
                break

            #Stack opcodes

            #PUSH32
            if opcode == 0x01:
                #Reads and pushes a 32 bit signed int to the data stack
                byte_arr_32 = bytearray()

                for x in range(4):
                    if self.instruction_pointer >= len(self.bytecode):
                        raise ValueError(" 'PUSH32' Requires at least four additional operand bytes in the bytecode")

                    byte_arr_32 += bytes([self.bytecode[self.instruction_pointer]])
                    self.instruction_pointer += 1

                int_32 = int.from_bytes(byte_arr_32, byteorder="big", signed=True)

                self.data_stack.append(int_32)

            #DUP
            elif opcode == 0x02:
                #Duplicates the top value of the data stack
                if len(self.data_stack) < 1:
                    raise ValueError(" 'DUP' requires at least one value on the data stack.")

                dup_val = self.data_stack[-1]

                self.data_stack.append(dup_val)

            #SWAP
            elif opcode == 0x03:
                #Swaps the top two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'SWAP' requires at least two values on the data stack.")

                self.data_stack[-1], self.data_stack[-2] = self.data_stack[-2], self.data_stack[-1]

            #DROP
            elif opcode == 0x04:
                #Discards the top element of the data stack
                if len(self.data_stack) < 1:
                    raise ValueError("'DROP' requires at least one value on the data stack.")

                self.data_stack.pop()

            #Arithmetic opcodes

            #ADD
            elif opcode == 0x10:
                #Adds the top two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'ADD' requires at least two values on the data stack.")

                right = self.data_stack[-1]
                left = self.data_stack[-2]

                Val_Sum = (right + left) & 0xFFFFFFFF

                if Val_Sum & 0x80000000:
                    Val_Sum -= 0x100000000

                self.data_stack[-2:] = [Val_Sum]

            #SUB
            elif opcode == 0x11:
                #Subtracts the top element from the second element of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'SUB' requires at least two values on the data stack.")

                right = self.data_stack[-1]
                left = self.data_stack[-2]

                Val_Sum = (left - right) & 0xFFFFFFFF

                if Val_Sum & 0x80000000:
                    Val_Sum -= 0x100000000

                self.data_stack[-2:] = [Val_Sum]

            #AND
            elif opcode == 0x12:
                #Bitwise AND of the top two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'AND' requires at least two values on the data stack.")

                right = self.data_stack[-1]
                left = self.data_stack[-2]

                Val_Sum = left & right

                self.data_stack[-2:] = [Val_Sum]

            #OR
            elif opcode == 0x13:
                #Bitwise OR of the top two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'OR' requires at least two values on the data stack.")

                right = self.data_stack[-1]
                left = self.data_stack[-2]

                Val_Sum = left | right

                self.data_stack[-2:] = [Val_Sum]

            #XOR
            elif opcode == 0x14:
                #Bitwise XOR of the top two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'XOR' requires at least two values on the data stack.")

                right = self.data_stack[-1]
                left = self.data_stack[-2]

                Val_Sum = left ^ right

                self.data_stack[-2:] = [Val_Sum]

            #NOT
            elif opcode == 0x15:
                #Bitwise NOT of the top element of the data stack
                if len(self.data_stack) < 1:
                    raise ValueError("'NOT' requires at least one values on the data stack.")

                right = self.data_stack[-1]

                Val_Sum = (~right) & 0xFFFFFFFF

                if Val_Sum & 0x80000000:
                    Val_Sum -= 0x100000000

                self.data_stack[-1:] = [Val_Sum]

            #Memory opcodes

            #LOAD32
            elif opcode == 0x20:
                #Loads a 32 bit value from memory and pushes it to the top of the stack
                if len(self.data_stack) < 1:
                    raise ValueError("'LOAD32' requires at least one value on the data stack.")

                Address = self.data_stack.pop()

                if not isinstance(Address, int):
                    raise TypeError("LOAD32 address must be an integer.")

                if not (0 <= Address <= len(self.memory) - 4):
                    raise ValueError("'LOAD32' address out of bounds.")

                bit32_value = int.from_bytes(self.memory[Address:Address+4], byteorder="big", signed=True)
                self.data_stack.append(bit32_value)

            #STORE32
            elif opcode == 0x21:
                #Stores a 32 bit value in memory from values at the top of the stack
                if len(self.data_stack) < 2:
                    raise ValueError("'STORE32' requires at least two values on the data stack.")

                Value = self.data_stack.pop()
                Address = self.data_stack.pop()

                if not isinstance(Address, int):
                    raise TypeError("STORE32 address must be an integer.")

                if not (0 <= Address <= len(self.memory) - 4):
                    raise ValueError("'STORE32' address out of bounds.")

                bit32_value = Value.to_bytes(4, byteorder="big", signed=True)

                self.memory[Address:Address+4] = bit32_value

            #Control opcodes

            #JMP
            elif opcode == 0x30:
                #Jumps to offset from the instruction start
                offset = struct.unpack(">h", self.bytecode[self.instruction_pointer:self.instruction_pointer+2])[0]
                self.instruction_pointer += 2

                self.instruction_pointer = instruction_start + offset

            #JZ
            elif opcode == 0x31:
                #Pops one value on the data stack, jumps if the value is zero
                if len(self.data_stack) < 1:
                    raise ValueError("'JZ' requires at least one value on the data stack.")

                Value = self.data_stack.pop()
                offset = struct.unpack(">h", self.bytecode[self.instruction_pointer:self.instruction_pointer+2])[0]

                self.instruction_pointer += 2
                if Value == 0:
                    self.instruction_pointer = instruction_start + offset

            #JNZ
            elif opcode == 0x32:
                #Pops one value on the data stack, jumps if the value isnt zero
                if len(self.data_stack) < 1:
                    raise ValueError("'JNZ' requires at least one value on the data stack.")

                Value = self.data_stack.pop()
                offset = struct.unpack(">h", self.bytecode[self.instruction_pointer:self.instruction_pointer+2])[0]

                self.instruction_pointer += 2
                if Value != 0:
                    self.instruction_pointer = instruction_start + offset

            #CALL
            elif opcode == 0x33:
                #Saves the return address onto the return stack, then jumps to the target
                offset = struct.unpack(">h", self.bytecode[self.instruction_pointer:self.instruction_pointer+2])[0]
                return_pos = self.instruction_pointer + 2

                self.return_stack.append(return_pos)

                self.instruction_pointer = instruction_start + offset

            #RET
            elif opcode == 0x34:
                #Reads a value from the return stack, returns the pointer to that position
                if len(self.return_stack) < 1:
                    raise ValueError("'RET' requires at least one value on the return stack.")

                return_pos = self.return_stack.pop()

                self.instruction_pointer = return_pos

            #System opcodes

            #SYSCALL
            elif opcode == 0x40:
                if self.instruction_pointer >= len(self.bytecode):
                    raise ValueError(" 'SYSCALL' Requires at least one additional index byte in the bytecode")

                index = self.bytecode[self.instruction_pointer]
                self.instruction_pointer += 1

                if index not in sys_call_table:
                    raise ValueError(f"'SYSCALL' index {index} is not in the syscall table.")

                handler = sys_call_table[index]
                result = handler(self)

                if result is not None:
                    self.data_stack.append(result)

            #Halt opcode

            #HALT
            elif opcode == 0xFF:
                self.is_halted = True

            else:
                raise ValueError(f"Unknown opcode: {opcode}")

#Executes bytecode and returns a snapshot of the VM state before wiping
def execute_bytecode(bytecode: bytearray | bytes, memory_size : int = 4096):

    vm = VirtualMachine(bytecode, memory_size)
    try:
        vm.run()
        result = {
            "is_halted": vm.is_halted,
            "instruction_pointer": vm.instruction_pointer,
            "data_stack": list(vm.data_stack),
            "return_stack": list(vm.return_stack),
            "memory": bytes(vm.memory),
        }
    finally:
        vm.wipe()

    return result
