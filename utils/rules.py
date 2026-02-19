import re

def decompose(keyword, in_str, script):
    """为给定关键字和字符串查找匹配的分解规则（如果可能）。

    参数
    ----------
    keyword : str
        用于从脚本查询分解规则的关键字。
    in_str : str
        用作分解规则输入的字符串。
    script : dict[]
        包含各种关键字分解规则的 JSON 对象。

    返回
    -------
    comps : str[]
        根据匹配的分解规则分解的组件列表。
        如果未找到匹配的分解规则则为空。
    reassembly_rule : str
        必须用于重组 comps 的重组规则。
        如果未找到匹配的分解规则则为空。

    """

    comps = []
    reassembly_rule = ''

    # 遍历脚本中的元素
    for d in script:
        if d['keyword'] == keyword:
            # 遍历该关键字的所有分解规则
            for rule in d['rules']:
                m = re.match(rule['decomp'], in_str, re.IGNORECASE)
                # 如果分解规则匹配
                if m:
                    # 根据分解规则分解字符串
                    comps = list(m.groups())
                    reassembly_rule = get_reassembly_rule(rule)
                    break
            break

    return comps, reassembly_rule

def reassemble(components, reassembly_rule):
    """给定重组规则重组字符串列表。
    注意：根据原始论文，重组规则是 1 索引的。

    参数
    ----------
    components : str[]
        要根据 `reassembly_rule` 组装的组件。
    reassembly_rule : str
        说明如何重组 `components` 的规则。

    返回
    -------
    response : str
        重组后的组件。

    """

    response = 'Eliza: '

    # 将重组规则拆分为其组件
    reassembly_rule = reassembly_rule.split()

    for comp in reassembly_rule:
        # 如果 comp 是数字，则放置该索引处的组件
        if comp.isnumeric():
            # int(comp)-1 是因为
            # Weizenbaum 表示法中的重组规则是 1 索引的
            response += components[int(comp)-1] + ' '
        # 否则，放置单词本身
        else:
            response += comp + ' '

    # 移除尾部空格
    response = response[:-1]

    return response

def process_decomp_rules(script, tags):
    """将脚本中的分解规则从 Weizenbaum 表示法处理为正则表达式。

    参数
    ----------
    script : dict[]
        包含 Weizenbaum 表示法分解规则的 JSON 对象。
    tags : dict[]
        标签数组，每个标签是同一语义场内的单词数组。

    返回
    -------
    script : dict[]
        包含正则表达式分解规则的 JSON 对象。

    """
    # 遍历 JSON 脚本中的每个字典
    for d in script:
        # 遍历每个字典中的所有规则
        for rule in d['rules']:
            # 将分解规则从 Weizenbaum 表示法转换为正则表达式
            rule['decomp'] = decomp_to_regex(rule['decomp'], tags)
    return script

def preprocess_decomp_rule(in_str):
    """在转换为正则表达式之前预处理分解规则。

    参数
    ----------
    in_str : str
        表示分解规则的字符串。

    返回
    -------
    in_str: str[]
        分解规则中的组件列表。
    """
    # 输入形式如下：例如 (0 YOU 0)
    # 去掉括号
    in_str = re.sub('[()]', '', in_str)

    # 将字符串拆分为空格分隔的列表
    return in_str.split()


def decomp_to_regex(in_str, tags):
    """将分解规则从 Weizenbaum 表示法转换为正则表达式。
    Weizenbaum 表示法的一个示例是：(0 KEYWORD1 0 KEYWORD2 0)。

    参数
    ----------
    in_str : str
        要转换为正则表达式的 Weizenbaum 表示法分解规则。
    tags : dict
        转换为正则表达式时要考虑的标签。

    返回
    -------
    out_str : str
        转换为正则表达式形式的分解规则。

    """
    out_str = ''

    in_str = preprocess_decomp_rule(in_str)

    for w in in_str:
        w = regexify(w, tags)
        # 需要括号以便正确地将句子划分为组件
        # \s* 匹配零个或多个空白字符
        out_str += '(' + w + r')\s*'

    return out_str

def regexify(w, tags):
    """将分解规则的单个组件
    从 Weizenbaum 表示法转换为正则表达式。

    参数
    ----------
    w : str
        分解规则的组件。
    tags : dict
        转换为正则表达式时要考虑的标签。

    返回
    -------
    w : str
        转换为正则表达式形式的分解规则组件。

    """
    # 0 表示"任意数量的单词"
    if w == '0':
        w = '.*'
    # 正的非零整数表示"这个特定数量的单词"
    elif w.isnumeric() and int(w) > 0:
        w = r'(?:\b\w+\b[\s\r\n]*){' + w + '}'
    # 以 @ 开头的单词表示标签
    elif w[0] == "@":
        # 获取标签名称
        tag_name = w[1:].lower()
        w = tag_to_regex(tag_name, tags)
    else:
        # 添加单词边界以在整体单词基础上匹配
        w = r'\b' + w + r'\b'
    return w

def tag_to_regex(tag_name, tags):
    """将分解规则标签转换为正则表达式表示法。

    参数
    ----------
    tag_name : str
        要转换为正则表达式的标签。
    tags : dict
        转换为正则表达式时要考虑的标签。

    返回
    -------
    w : str
        转换为正则表达式表示法的标签。如果 `tag_name` 不在 `tags` 中则为空。
    """
    w = ''
    if tag_name in tags:
        # 创建一个正则表达式，用 OR 运算符分隔每个选项（例如 x|y|z）
        w = r'\b(' + '|'.join(tags[tag_name]) + r')\b'
    return w

def update_last_used_reassembly_rule(rule):
    """更新给定分解 `rule` 的 `last_used_reassembly_rule` ID。
    如果相应分解规则的所有重组规则都已使用，则循环回到 0。

    参数
    ----------
    rule : dict
        包含分解规则的规则，
        一个或多个重组规则和 `last_used_reassembly_rule` 计数器。

    返回
    -------
    next_id : int
        要为输入 `rule` 的 `last_used_reassembly_rule` 分配的值。
    """

    # 更新最后使用的重组规则 ID
    next_id = rule['last_used_reassembly_rule']+1
    # 如果所有重组规则都已使用，则重新开始
    if next_id >= len(rule['reassembly']):
        next_id = 0
    rule['last_used_reassembly_rule'] = next_id

def reset_all_last_used_reassembly_rule(script):
    """将脚本中的所有 `last_used_reassembly_rule` 重置为 0。

    参数
    ----------
    script : dict[]
        包含关键字和相关规则的 JSON 对象。
    """

    for d in script:
        for rule in d['rules']:
            rule['last_used_reassembly_rule'] = 0

def get_reassembly_rule(rule):
    """返回给定分解规则的重组规则。

    参数
    ----------
    rule : dict
        包含分解规则的规则，
        一个或多个重组规则和 `last_used_reassembly_rule` 计数器。

    返回
    -------
    reassembly_rule : str
        用于为用户组装响应的重组规则。
    """
    reassembly_rule = rule['reassembly'][rule['last_used_reassembly_rule']]
    update_last_used_reassembly_rule(rule)
    return reassembly_rule
