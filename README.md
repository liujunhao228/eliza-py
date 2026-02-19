# eliza.py
**ELIZA** 是一个自然语言处理程序，由 Joseph Weizenbaum 于 1964 年至 1966 年间开发，
最初使用 MAD-SLIP 实现。
你可以 [这里](https://dl.acm.org/doi/10.1145/365153.365168) 阅读 1966 年的论文。

ELIZA 使用模式匹配、分解和重组规则
来模拟罗杰式心理治疗师。

![演示](./demo.svg)
（输入取自 [Weizenbaum 1966 年的论文，第 1-2 页。](https://dl.acm.org/doi/10.1145/365153.365168)）

# 程序流程

![流程图](./flowchart.svg)

# 下载
## 依赖要求
- Python 3.x
（通过调整某些命令的语法，应该也可以与 Python 2 一起使用）

## 通过命令行
```bash
# 克隆仓库
$ git clone https://github.com/rdimaio/eliza-py
```

# 使用方法
## 启动程序
```bash
# 进入项目文件夹
$ cd eliza-py

# 执行文件
$ python eliza.py
Eliza: 你好。
You: [输入一些内容]
```

## 对话示例（使用与原始论文相同的输入，第 1-2 页）
```
You: Men are all alike.
Eliza: In what way?
You: They're always bugging us about something or other.
Eliza: Can you think of a specific example?
You: Well, my boyfriend made me come here.
Eliza: Your boyfriend made you come here?
You: He says I'm depressed much of the time.
Eliza: I am sorry to hear that you are depressed.
You: It's true. I am unhappy.
Eliza: Do you think coming here will help you not to be unhappy?
You: I need some help, that much seems certain.
Eliza: What would it mean to you if you got some help?
You: Perhaps I could learn to get along with my mother.
Eliza: Tell me more about your family.
```

## 退出程序
```bash
# 你可以输入 bye、goodbye、done、quit 或 exit。或者使用 CTRL+C，如果你想粗鲁一点的话……
You: bye
Eliza: 再见。
```

# 脚本结构

## `scripts/general.json`
此脚本处理通用英语语言信息，这些信息不一定与其他脚本相关联，
以及程序有用的输入。

- `substitutions`：指定在应用自定义脚本之前应替换哪些关键字
- `tags`：指定同一语义场内的关键字
- `memory_inputs`：关键字数组，提示生成添加到内存堆栈的额外响应
- `exit_inputs`：可用于退出程序的关键字数组

## `scripts/doctor.json`
此脚本模拟**罗杰式心理治疗师**。
它已根据原始论文附录（第 9 页）填充，包括等级。
另一个很好的参考资料是 [Charles Hayen 的 ELIZA Java 实现](http://chayden.net/eliza/Eliza.html) 的脚本文件。
为了使程序感觉更友好，做了一些小的补充（例如，程序会回应问候语）。

JSON 文件中的每个元素都遵循以下结构：
- `keyword`：程序在用户输入中查找的关键字（**替换后**，与原始实现相同）
    - 存在两个特殊关键字：
        - `$`：指定应给出通用答案
        - `^`：指定应给出内存堆栈中的答案
- `rank`：该关键字的等级
- `rules`：分解规则和匹配重组规则的数组，形式为：
    - `decomp`：分解规则（使用与 1966 年原始论文相同的语法）
    - `reassembly`：要与 `decomp` 中指定的分解规则一起使用的重组规则数组
        - 重组规则使用与原始论文相同的 1 索引；
        注意，当分解规则中的 `tag` 等同于
        其重组规则中的两个组件而不是一个
        （以便能够使用正则表达式）
    - `last_used_reassembly_rule`：此分解规则最后使用的重组规则的 ID（0 索引）；
        每次匹配分解规则时都会递增，
        当使用完数组中的最后一个重组规则时会循环回到开头。


# 常见问题

## 与原始实现的差异

- **关键字排名**：
    - 原始实现：关键字不保证按降序排列；
    如原始论文第 4 页图 2 所示，如果关键字的等级高于
    到目前为止句子中遇到的最高等级，则将其放置在关键字堆栈的顶部，
    否则将其放置在关键字堆栈的底部。
    - 此实现：关键字保证按降序排列。
- **句子分词**：
    - 原始实现：如果遇到逗号/句号且已找到关键字，
    则所有后续文本都会被删除（第 2 页）。
    - 此实现：句子根据标点符号（—,.:;-）拆分，
    并选择具有最高等级关键字的句子进行分解。
    - 主要原因：
        - 用户输入的重点不一定在句子的第一部分
        - 具有最高等级关键字的部分更有可能具有该关键字的分解规则，
        因为它首先具有等级
- **标签**：
    - 原始实现：使用 `DLIST` 表示标签。
    - 此实现：使用 `tag` 表示标签。
    - 功能相同。
- **内存堆栈**：
    - 原始实现：关键字 `my` 与内存堆栈关联（第 6 页）；
    - 此实现：当找不到匹配的分解规则时调用内存堆栈。

## 为什么脚本存储在 JSON 中而不是 CSV？
在 `doctor` 脚本中，每个关键字都有**可变数量**的分解规则，
每个分解规则都有**可变数量**的重组规则。
我认为 JSON 可以以更直观的方式存储此信息结构。

`general` 脚本可以存储在 `.csv` 中，因为没有嵌套，
但我更喜欢再次使用 JSON 以与另一个脚本保持一致。

# 未来工作
- 允许用户在会话期间通过输入"edit"来编辑脚本，如原始实现中所述（论文第 7 页）
- 翻译成其他语言（意大利语、西班牙语……）
- 考虑在程序响应之前包含随机延迟，增强对话的拟人感

# 参考资料
- J. Weizenbaum, "ELIZA-a computer program for the study of natural language communication between man and machine," Communications of the ACM, vol. 9, no. 1, pp. 36–45, Jan. 1966. [链接](https://dl.acm.org/doi/10.1145/365153.365168)

- [Charles Hayen 的 ELIZA Java 实现](http://chayden.net/eliza/Eliza.html) 的脚本文件

## 工具

- **演示动画**：[asciinema](https://github.com/asciinema/asciinema) 和 [termtosvg](https://github.com/nbedos/termtosvg)
- **流程图**：[draw.io](draw.io)
