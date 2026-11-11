import sys
import json
import struct

# --- 常量定义 ---
AOK, HLT, ADR, INS = 1, 2, 3, 4

RAX, RCX, RDX, RBX, RSP, RBP, RSI, RDI = 0, 1, 2, 3, 4, 5, 6, 7
R8, R9, R10, R11, R12, R13, R14, RNONE = 8, 9, 10, 11, 12, 13, 14, 15

I_HALT, I_NOP, I_RRMOVQ, I_IRMOVQ = 0, 1, 2, 3
I_RMMOVQ, I_MRMOVQ, I_ALU, I_JMP = 4, 5, 6, 7
I_CALL, I_RET, I_PUSHQ, I_POPQ = 8, 9, 10, 11

class Y86Simulator:
    def __init__(self, mem_size=8192):
        self.REG_NAMES = {
            0: "rax", 1: "rcx", 2: "rdx", 3: "rbx", 4: "rsp", 5: "rbp", 6: "rsi", 7: "rdi",
            8: "r8", 9: "r9", 10: "r10", 11: "r11", 12: "r12", 13: "r13", 14: "r14"
        }
        self.mem_size = mem_size
        self.memory = bytearray(mem_size)
        self.PC = 0
        self.STAT = AOK
        
        self.REG = {i: 0 for i in range(15)}
        self.REG[RNONE] = 0 
        
        self.CC = {"ZF": 1, "SF": 0, "OF": 0}
        
        # CPU 内部暂存器 / 数据通路状态变量 (用于在多周期状态机的各阶段间传递当前指令的数据)
        self.icode = I_NOP
        self.ifun = 0
        self.rA = RNONE
        self.rB = RNONE
        self.valC = 0
        self.valP = 0
        self.valA = 0
        self.valB = 0
        self.valE = 0
        self.valM = 0
        self.Cnd = False

        self.trace = []

    # ---------------- 辅助方法 ----------------
    def to_signed64(self, val):
        """将无符号 64 位整数截断并转换为有符号补码整数"""
        val = val & 0xFFFFFFFFFFFFFFFF
        if val & 0x8000000000000000:
            val -= 0x10000000000000000
        return val
    
    def sign_extend(self, val, bits=64):
        """将指定位数的无符号整数转换为补码有符号整数"""
        sign_bit = 1 << (bits - 1)
        return (val & (sign_bit - 1)) - (val & sign_bit)
    
    def uint64(self, val):
        """将数值截断为 64 位无符号整数"""
        return val & 0xFFFFFFFFFFFFFFFF
        
    def read_mem(self, addr, size):
        """从指定内存地址读取指定字节数的数据，若地址越界则触发 ADR 异常"""
        if addr < 0 or addr + size > self.mem_size:
            self.STAT = ADR
            return 0
        data = self.memory[addr : addr+size]
        if size == 1:
            return data[0]
        elif size == 8:
            return struct.unpack('<Q', data)[0]
        return 0

    def write_mem(self, addr, size, val):
        """将数据写入指定的内存地址，若地址越界则触发 ADR 异常"""
        if addr < 0 or addr + size > self.mem_size:
            self.STAT = ADR
            return
        if size == 8:
            self.memory[addr : addr+size] = struct.pack('<Q', self.uint64(val))
            
    def check_cond(self, ifun):
        """根据当前条件码寄存器，判断跳转或条件传送是否满足"""
        zf, sf, of = self.CC["ZF"], self.CC["SF"], self.CC["OF"]
        if ifun == 0: return True                  
        if ifun == 1: return (sf ^ of) | zf        
        if ifun == 2: return sf ^ of               
        if ifun == 3: return zf                    
        if ifun == 4: return not zf                
        if ifun == 5: return not (sf ^ of)         
        if ifun == 6: return not (sf ^ of) and not zf 
        return False

    # ---------------- 核心 FSM 逻辑 (需实现) ----------------
    
    def fetch(self):
        """
        取指阶段 (Fetch)
        任务:
        1. 从 self.PC 指向的内存地址读取指令字节 (icode 和 ifun)。
           如果内存地址非法，将 self.STAT 置为 ADR 并 return。
        2. 验证 icode 的合法性。如果不属于标准指令集，将 self.STAT 置为 INS 并 return。
           如果遇到 halt 指令，将 self.STAT 置为 HLT 并 return。
        3. 根据 icode 判断该指令是否需要寄存器指示符字节 (need_reg) 和 8 字节常数 (need_valC)。
        4. 如果 need_reg，读取寄存器指示符并分别赋值给 self.rA 和 self.rB。
        5. 如果 need_valC，读取 8 字节常数赋值给 self.valC。
        6. 计算出下一条指令的地址，并赋值给 self.valP。
        
        提示: 使用 read_mem(addr, size) 读取内存。注意更新地址偏移量。
        """
        if self.PC < 0 or self.PC >= self.mem_size:
            self.STAT = ADR
            return
            
        byte0 = self.read_mem(self.PC, 1)
        if self.STAT != AOK: return
        
        # 已经为你提取出了当前指令的操作码，请保留下方两条赋值，继续向下实现
        self.icode = byte0 >> 4
        self.ifun = byte0 & 0x0F

        # inode check
        if self.icode not in range(12):
            self.STAT = INS
            return
        
        if self.icode == I_HALT:
            self.STAT = HLT
            return

        # need_reg
        if self.icode in [I_RRMOVQ, I_IRMOVQ, I_RMMOVQ, I_MRMOVQ, I_ALU, I_PUSHQ, I_POPQ]:
            byte1 = self.read_mem(self.PC + 1, 1)
            self.rA = byte1 >> 4
            self.rB = byte1 & 0x0F

        # need_valC and 10 bytes
        if self.icode in [I_IRMOVQ, I_RMMOVQ, I_MRMOVQ]:
            self.valC = self.read_mem(self.PC + 2, 8)
            self.valP = self.PC + 10
            
        # need_valc and 9 bytes
        if self.icode in [I_JMP, I_CALL]:
            self.valC = self.read_mem(self.PC + 1, 8)
            self.valP = self.PC + 9

        # 1 byte
        if self.icode in [I_HALT, I_NOP, I_RET]:
            self.valP = self.PC + 1

        # 2 bytes 
        if self.icode in [I_RRMOVQ, I_ALU, I_PUSHQ, I_POPQ]:
            self.valP = self.PC + 2


    def decode(self):
        """
        译码阶段 (Decode)
        任务:
        1. 根据 self.icode 判断需要读取哪些寄存器，设置 srcA 和 srcB。
           注意：某些指令（如 pushq, popq, call, ret）隐式使用 %rsp 作为源操作数，需特殊处理。
        2. 从寄存器文件 (self.REG) 中读取 srcA 和 srcB 的值，分别赋值给 self.valA 和 self.valB。
           如果 src 不存在 (RNONE)，则读取值为 0。
        """
        srcA = RNONE
        srcB = RNONE

        # rA, rB
        if self.icode in [I_RMMOVQ, I_ALU]:
            srcA = self.rA
            srcB = self.rB

        # rA, RNONE
        if self.icode == I_RRMOVQ:
            srcA = self.rA

        # RNONE, rB
        if self.icode == I_MRMOVQ:
            srcB = self.rB

        # rA, rsp
        if self.icode == I_PUSHQ:
            srcA = self.rA
            srcB = RSP

        # rsp, rsp
        if self.icode in [I_POPQ, I_RET]:
            srcA = RSP
            srcB = RSP

        # RNONE, rsp
        if self.icode == I_CALL:
            srcB = RSP

        self.valA = self.REG.get(srcA, 0)
        self.valB = self.REG.get(srcB, 0)
        

    def execute(self):
        """
        执行阶段 (Execute)
        任务:
        1. 初始化 self.valE = 0 和 self.Cnd = False。
        2. 为 ALU 运算准备操作数 aluA 和 aluB。它们的值取决于当前的指令 (self.icode)。
           例如：算术运算时，aluA 取 valA，aluB 取 valB；
                 内存访问指令 (rmmovq, mrmovq) 需计算地址，aluA 取 valC，aluB 取 valB。
                 栈操作时，需进行 +8 或 -8 运算。
        3. 执行 ALU 逻辑：
           - 如果是普通地址计算，直接 valE = aluB + aluA (需截断至64位无符号整数，可调用 uint64)。
           - 如果是 OPq 指令 (I_ALU)，根据 self.ifun 执行相应的加减或位运算，
             并将结果赋值给 self.valE。
             * 重要：如果是 OPq 指令，还需根据运算结果正确更新条件码寄存器 self.CC ("ZF", "SF", "OF")。
               请使用 self.sign_extend() 将无符号数转为有符号数进行带符号运算和溢出判定。
        4. 条件判断 (针对 jXX 和 cmovXX)：调用 self.check_cond(self.ifun) 获取条件是否成立，赋值给 self.Cnd。
        """
        self.valE = 0
        self.Cnd = False
        
        aluA = 0
        aluB = 0
        
        # prepare aluA and aluB
        if self.icode in [I_RMMOVQ, I_MRMOVQ]:
            aluA = self.valC
            aluB = self.valB

        if self.icode == I_ALU:
            aluA = self.valA
            aluB = self.valB

        # directly address calculation
        if self.icode in [I_CALL, I_PUSHQ]:
            self.valE = self.uint64(self.valB - 8)

        if self.icode in [I_RET, I_POPQ]:
            self.valE = self.uint64(self.valB + 8)

        # ALU calculation
        if self.icode in [I_RMMOVQ, I_MRMOVQ]:
            self.valE = self.uint64(aluB + aluA)

        if self.icode == I_ALU:
            aluA = self.sign_extend(aluA)
            aluB = self.sign_extend(aluB)

            if self.ifun == 0: # addq
                self.valE = self.uint64(aluB + aluA)
            elif self.ifun == 1: # subq
                self.valE = self.uint64(aluB - aluA)
            elif self.ifun == 2: # andq
                self.valE = self.uint64(aluB & aluA)
                self.CC["OF"] = 0
            elif self.ifun == 3: # xorq
                self.valE = self.uint64(aluB ^ aluA)
                self.CC["OF"] = 0
            
            self.valE = self.sign_extend(self.valE)
            self.CC["ZF"] = 1 if self.valE == 0 else 0
            self.CC["SF"] = 1 if self.valE < 0 else 0
            if self.ifun == 0: # addq
                self.CC["OF"] = 1 if (aluA > 0 and aluB > 0 and self.valE < 0) or (aluA < 0 and aluB < 0 and self.valE >= 0) else 0
            elif self.ifun == 1: # subq
                self.CC["OF"] = 1 if (aluA < 0 and aluB >= 0 and self.valE < 0) or (aluA > 0 and aluB < 0 and self.valE >= 0) else 0

        # no calculation for rrmovq or irmovq
        # they need valE for write back
        if self.icode == I_RRMOVQ:
            self.valE = self.valA

        if self.icode == I_IRMOVQ:
            self.valE = self.valC

        self.Cnd = self.check_cond(self.ifun)
        
    def memory_stage(self):
        """
        访存阶段 (Memory)
        任务:
        1. 根据指令类型确定内存访问的地址 (addr)。通常为 valE 或 valA。
        2. 判断是否需要写内存 (I_RMMOVQ, I_PUSHQ, I_CALL)。
           如果是，调用 self.write_mem(addr, 8, value) 将相应的值写入内存。
           注意：不同的指令写入内存的数据不同 (例如 PUSHQ 写入 valA，CALL 写入 valP)。
        3. 判断是否需要读内存 (I_MRMOVQ, I_POPQ, I_RET)。
           如果是，调用 self.read_mem(addr, 8) 读取 8 字节数据，并赋值给 self.valM。
        """
        self.valM = 0

        # valE
        if self.icode in [I_PUSHQ, I_CALL, I_RMMOVQ, I_MRMOVQ]:
            addr = self.valE

        # valA
        if self.icode in [I_POPQ, I_RET]:
            addr = self.valA # old rsp

        # write memory
        if self.icode == I_PUSHQ or self.icode == I_RMMOVQ:
            self.write_mem(addr, 8, self.valA)
        elif self.icode == I_CALL:
            self.write_mem(addr, 8, self.valP)

        # read memory
        if self.icode in [I_POPQ, I_RET, I_MRMOVQ]:
            self.valM = self.read_mem(addr, 8)
        

    def write_back(self):
        """
        写回阶段 (Write Back)
        任务:
        1. 确定 valE 的目标寄存器 (dstE)。通常为 rB，栈操作时为 %rsp。
           注意：如果是 cmovXX，只有当 self.Cnd 为 True 时，才将结果写回。
        2. 确定 valM 的目标寄存器 (dstM)。通常为 rA。
        3. 如果目标寄存器不是 RNONE，将对应的值 (valE 或 valM) 写入对应的寄存器。
           注意：依据 CS:APP Y86-64 异常栈语义，弹栈到 %rsp 时（如 popq %rsp），
           如果 dstE 和 dstM 同为 %rsp，需确保从内存读出的 valM 能最终覆盖掉运算得出的 valE。
        """
        dstE = RNONE
        dstM = RNONE

        if self.icode in [I_POPQ, I_MRMOVQ]:
            dstM = self.rA

        if self.icode in [I_ALU, I_RRMOVQ, I_IRMOVQ]:
            dstE = self.rB
        elif self.icode in [I_PUSHQ, I_POPQ, I_CALL, I_RET]:
            dstE = RSP

        # for I_POPQ, valM should overwrite valE, so dstE is first
        if dstE != RNONE:
            if self.icode == I_RRMOVQ and not self.Cnd:
                pass  
            else:
                self.REG[dstE] = self.valE
        if dstM != RNONE:
            self.REG[dstM] = self.valM

    def update_pc(self):
        """
        更新 PC 阶段 (Update PC)
        任务:
        根据指令类型和条件码决定下一个周期的 PC 值。
        - call 指令：PC 更新为调用目标 (valC)。
        - jXX 指令：当条件成立 (Cnd 为真) 时更新为目标地址 (valC)。
        - ret 指令：PC 更新为从栈中弹出的返回地址 (valM)。
        - 其它默认情况：PC 顺序更新为下一条指令的地址 (valP)。
        """
        if self.icode == I_CALL:
            self.PC = self.valC
        elif self.icode == I_JMP and self.Cnd:
            self.PC = self.valC
        elif self.icode == I_RET:
            self.PC = self.valM
        else:
            self.PC = self.valP

    # ---------------- JSON 序列化输出 ----------------
    def dump_state(self):
        """将当前状态转存为字典"""
        mem_dump = {}
        for addr in range(0, self.mem_size, 8):
            val = struct.unpack('<q', self.memory[addr:addr+8])[0]
            if val != 0:
                mem_dump[str(addr)] = val

        state = {
            "CC": dict(self.CC),
            "MEM": mem_dump,
            "PC": self.PC,
            "REG": {self.REG_NAMES[k]: self.to_signed64(v) for k, v in sorted(self.REG.items()) if k != RNONE},
            "STAT": self.STAT
        }
        self.trace.append(state)

    # ---------------- 入口流转 ----------------
    def load_program(self, file_obj):
        """解析器 Parser"""
        for line in file_obj:
            idx = line.find('|')
            code_part = line[:idx].strip() if idx != -1 else line.strip()
            if not code_part: continue
            if ':' in code_part:
                addr_str, data_str = code_part.split(':', 1)
                addr_str, data_str = addr_str.strip(), data_str.strip()
                if addr_str and data_str:
                    addr = int(addr_str, 16)
                    data_bytes = bytes.fromhex(data_str)
                    for i, b in enumerate(data_bytes):
                        if addr + i < len(self.memory):
                            self.memory[addr + i] = b

    def run(self):
        """主循环：时钟步进"""
        while self.STAT == AOK:
            self.fetch()
            if self.STAT != AOK: 
                self.dump_state()
                break
                
            self.decode()
            self.execute()
            self.memory_stage()
            
            self.write_back()
            
            if self.STAT != AOK: 
                self.dump_state()
                break
                
            self.update_pc()
            self.dump_state()
            
        print(json.dumps(self.trace, indent=4))

if __name__ == "__main__":
    sim = Y86Simulator()
    sim.load_program(sys.stdin)
    sim.run()