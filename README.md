# Y86-64 Simulator (Python 框架)

## 简介

在本实验中，你将实现一个 Y86-64 指令集 CPU 模拟器。此仓库中，我们在 `cpu.py` 中已经为你搭建好了文件解析器（Parser）和主循环骨架。你的任务是补全各个执行阶段的核心数据通路逻辑。

```bash
.
├─ test/           # 测试指令文件 (.yo 机器码文件)
├─ answer/         # 指令执行的标准结果快照 (.json)
├─ test.py         # 自动化评测脚本：运行模拟器 + 严格比对结果
└─ cpu.py          # 你需要完善的模拟器源代码
```

## 测试方法

请确保在 Python 3 环境下运行。使用以下命令进行自动化测试与评分：

```bash
python test.py --bin "python cpu.py"
```

如果你只想测试单个文件以观察输出格式，可以使用标准输入重定向：
```bash
python cpu.py < test/abs-asum-cmov.yo
```

---

## 实验任务

为了通过所有测试用例，你需要在 `cpu.py` 相应的 `TODO` 处实现以下 Y86-64 核心指令集的逻辑：

- **数据传送指令**：`irmovq`, `rrmovq`, `mrmovq`, `rmmovq`
- **条件传送指令**：`cmovXX` (包括 `cmovle`, `cmovl`, `cmove`, `cmovne`, `cmovge`, `cmovg`)
- **算术与逻辑运算指令 (`OPq`)**：`addq`, `subq`, `andq`, `xorq`（需正确更新 `ZF`, `SF`, `OF` 条件码）
- **分支与跳转指令**：`jmp` (无条件跳转) 以及 `jXX` (条件跳转，如 `je`, `jne`, `jle` 等)
- **函数调用与栈操作**：`pushq`, `popq`, `call`, `ret`
- **系统控制**：`halt`, `nop`

完成后请把仓库链接提交至 E-Learning 平台。

你需要另行准备用于汇报的演示文稿，并单独提交到 E-Learning 平台的另一个作业上。
