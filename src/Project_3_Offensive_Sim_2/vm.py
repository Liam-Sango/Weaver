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
            self.instruction_pointer += 1

            # Stack OPCODES

            #PUSH32
            if opcode == 0x01:
                #Reads and pushes 32 bit int to the data stack.
                byte_arr_32 = bytearray()
    
                for x in range(4):
                    if self.instruction_pointer >= len(self.bytecode):
                        raise ValueError ("operand bytes missing for PUSH32")
                    
                    byte_arr_32 += self.bytecode[self.instruction_pointer]
                    self.instruction_pointer += 1

                int_32 = int.from_bytes(byte_arr_32, byteorder="big")

                self.data_stack.append(int_32)

            #DUP
            elif opcode == 0x02:
                #Reads and duplicates the top value of the data stack
                if len(self.data_stack) < 1:
                    raise ValueError("Data stack values missing for DUP")
                
                dup_val = self.data_stack[-1]

                self.data_stack.append(dup_val)
                
            #SWAP
            elif opcode == 0x03:
                # Reads and swaps top  two elements of the data stack
                if len(self.data_stack) < 2:
                    raise ValueError("Data stack values missing for SWAP")
                
                self.data_stack[-1], self.data_stack[-2] = self.data_stack[-2], self.data_stack[-1]

            #DROP
            elif opcode == 0x04:
                print("TEMP")

            # Arithmetic OPCODES
            
            #ADD
            elif opcode == 0x10:
                print("TEMP")
            #SUB
            elif opcode == 0x11:
                print("TEMP")
            #AND
            elif opcode == 0x12:
                print("TEMP")
            #OR
            elif opcode == 0x13:
                print("TEMP")
            #XOR
            elif opcode == 0x14:
                print("TEMP")
            #NOT
            elif opcode == 0x15:
                print("TEMP")
            

             # Memory OPCODES
            
            #LOAD32
            elif opcode == 0x20:
                print("TEMP")
            #STORE32
            elif opcode == 0x21:
                print("TEMP")

            #Control OPCODES
            
            #JMP
            elif opcode == 0x30:
                print("TEMP")
            #JZ
            elif opcode == 0x31:
                print("TEMP")
            #JNZ
            elif opcode == 0x32:
                print("TEMP")
            #CALL
            elif opcode == 0x33:
                print("TEMP")
            #RET
            elif opcode == 0x33:
                print("TEMP")


            #System OPCODES
            
            #JMP
            elif opcode == 0x40:
                print("TEMP")

            #Halt OPCODE

            #HALT
            elif opcode == 0xFF:
                print("TEMP")


            else: 
                raise ValueError (f"Unknown opcode: {opcode}")


def execute_bytecode(bytecode: bytearray | bytes, memory_size : int = 4096):

    vm = VirtualMachine(bytecode, memory_size)
    vm.run()

    return vm
    
