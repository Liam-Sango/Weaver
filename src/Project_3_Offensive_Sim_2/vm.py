import struct
import logging

# Configure syscall logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_function_call(func):
    def wrapper(*args, **kwargs):
        logger.info(f'Calling {func.__name__} with args: {args}, kwargs: {kwargs}')
        result = func(*args, **kwargs)
        logger.info(f'{func.__name__} returned: {result}')
        return result
    return wrapper


#SYSCALL FUNCTIONS

 # FILE HANDLING
@log_function_call
def file_read(vm):
    length = vm.data_stack.pop()
    address = vm.data_stack.pop()
    return 0

@log_function_call
def file_write(vm):
    length = vm.data_stack.pop()
    address = vm.data_stack.pop()
    return 0


 # NETWORK HANDLING
@log_function_call
def tcp_connect(vm):
    port = vm.data_stack.pop()
    host_addr = vm.data_stack.pop()
    return 0

@log_function_call
def dns_lookup(vm):
    hostname_addr = vm.data_stack.pop()
    return 0

@log_function_call
def sleep(vm):
    milliseconds = vm.data_stack.pop()
    return 0

@log_function_call
def http_get(vm):
    dest_addr = vm.data_stack.pop()
    url_addr = vm.data_stack.pop()
    return 0


#SYSCALL TABLES 

sys_call_table = {
    # FILE HANDLING

    0: file_read,
    1: file_write,

    # NETWORK HANDLING

    2: tcp_connect,
    3: dns_lookup, 
    4: sleep,
    5: http_get,
}

class VirtualMachine:
       
    def __init__(self, bytecode, memory_size=4096):
           
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
   
    def run(self):

        while not self.is_halted and self.instruction_pointer < len(self.bytecode):

            opcode = self.bytecode[self.instruction_pointer]
            instruction_start = self.instruction_pointer
            self.instruction_pointer += 1

            # Stack OPCODES

            #PUSH32
            if opcode == 0x01:
                #Reads and pushes 32 bit int to the data stack.
                byte_arr_32 = bytearray()
    
                for x in range(4):
                    if self.instruction_pointer >= len(self.bytecode):
                        raise ValueError (" 'PUSH32' Requires at least four additional operand bytes in the bytecode")
                    
                    byte_arr_32 += self.bytecode[self.instruction_pointer]
                    self.instruction_pointer += 1

                int_32 = int.from_bytes(byte_arr_32, byteorder="big")

                self.data_stack.append(int_32)

            #DUP
            elif opcode == 0x02:
                #Reads and duplicates the top value of the data stack
                if len(self.data_stack) < 1:
                    raise ValueError(" 'DUP' requires at least one value on the data stack.")
                
                dup_val = self.data_stack[-1]

                self.data_stack.append(dup_val)
                
            #SWAP
            elif opcode == 0x03:
                # Reads and swaps top  two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'SWAP' requires at least two values on the data stack.")
                
                self.data_stack[-1], self.data_stack[-2] = self.data_stack[-2], self.data_stack[-1]

            #DROP
            elif opcode == 0x04:
                #Discards the top element of the data stack
                if len(self.data_stack) < 1:
                    raise ValueError("'DROP' requires at least one value on the data stack.")
                
                self.data_stack.pop()
            

            # Arithmetic OPCODES
            
            #ADD
            elif opcode == 0x10:
                #performs an adddition operation of the top two elements of the data stack
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
                 #performs an subtraction operation of the top two elements of the data stack
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
                #performs a bitwise AND operation of the top two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'AND' requires at least two values on the data stack.")
                
                right = self.data_stack[-1]
                left = self.data_stack[-2]

                Val_Sum = left & right

                self.data_stack[-2:] = [Val_Sum]

            #OR
            elif opcode == 0x13:
                #performs a bitwise OR operation of the top two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'OR' requires at least two values on the data stack.")
                
                right = self.data_stack[-1]
                left = self.data_stack[-2]

                Val_Sum = left | right

                self.data_stack[-2:] = [Val_Sum]

            #XOR
            elif opcode == 0x14:
                #performs a bitwise XOR operation of the top two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("'XOR' requires at least two values on the data stack.")
                
                right = self.data_stack[-1]
                left = self.data_stack[-2]

                Val_Sum = left ^ right

                self.data_stack[-2:] = [Val_Sum]

            #NOT
            elif opcode == 0x15:
                #performs an bitwise NOT operation of the top two elements of the data stack
                if len(self.data_stack) < 1:
                    raise ValueError("'NOT' requires at least one values on the data stack.")
                
                right = self.data_stack[-1]

                Val_Sum = (~right) & 0xFFFFFFFF
                
                if Val_Sum & 0x80000000:
                     Val_Sum -= 0x100000000

                self.data_stack[-1:] = [Val_Sum]
            

            # Memory OPCODES
            
            #LOAD32
            elif opcode == 0x20:
                 #loads 32 bit value from memory and pushes it to the top of the stack
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
                #Stores 32 bit value in memory from values at the top of the stack
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

            #Control OPCODES
            
            #JMP
            elif opcode == 0x30:
                #Jumps to offset from the instruction start.
                offset = struct.unpack(">h", self.bytecode[self.instruction_pointer:self.instruction_pointer+2])[0]
                self.instruction_pointer += 2

                self.instruction_pointer = instruction_start + offset

            #JZ
            elif opcode == 0x31:
                 #Pops one value on the data stack, Jumps if the value is zero.
                 if len(self.data_stack) < 1:
                    raise ValueError("'JZ' requires at least one value on the data stack.")
                 
                 Value = self.data_stack.pop()
                 offset = struct.unpack(">h", self.bytecode[self.instruction_pointer:self.instruction_pointer+2])[0]
                 
                 self.instruction_pointer += 2
                 if Value == 0:
                      self.instruction_pointer = instruction_start + offset

            #JNZ
            elif opcode == 0x32:
                #Pops one value on the data stack, Jumps if the value isnt zero.
                 if len(self.data_stack) < 1:
                    raise ValueError("'JNZ' requires at least one value on the data stack.")
                 
                 Value = self.data_stack.pop()
                 offset = struct.unpack(">h", self.bytecode[self.instruction_pointer:self.instruction_pointer+2])[0]
                 
                 self.instruction_pointer += 2
                 if Value != 0:
                      self.instruction_pointer = instruction_start + offset

            #CALL
            elif opcode == 0x33:
                #reads a relative jump offset, saves the return address onto the return stack, then jumps to the target
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


            # System OPCODES
            
            
            #SYSCALL
            elif opcode == 0x40:
                if self.instruction_pointer >= len(self.bytecode):
                        raise ValueError (" 'SYSCALL' Requires at least one additional index byte in the bytecode")
                
                index = self.bytecode[self.instruction_pointer]
                self.instruction_pointer += 1

                if index not in sys_call_table:
                     raise ValueError (f"'SYSCALL' index {index} is not in the syscall table.")

                handler = sys_call_table[index]
                result = handler(self)

                if result is not None:
                    self.data_stack.append(result)

            #Halt OPCODE

            #HALT
            elif opcode == 0xFF:
                self.is_halted = True


            else: 
                raise ValueError (f"Unknown opcode: {opcode}")


def execute_bytecode(bytecode: bytearray | bytes, memory_size : int = 4096):

    vm = VirtualMachine(bytecode, memory_size)
    vm.run()

    return vm
    
