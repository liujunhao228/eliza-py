import re

from utils.rank import rank
from utils.rules import decompose, reassemble

def generate_response(in_str, script, substitutions, memory_stack, memory_inputs):
    """根据脚本从用户输入生成响应。

    参数
    ----------
    in_str : str
        用户输入。
    script : dict[]
        包含关键字和规则信息的 JSON 对象。
    substitutions : dict
        键值对，其中键 = 要替换的单词，值 = 新单词。
    memory_stack : str[]
        当 `generate_memory_response` 被提示时生成的响应堆栈。
    memory_inputs : str[]
        提示 `generate_memory_response` 的关键字。

    返回
    -------
    response : str
        生成的响应。

    """
    # 将输入分解为由标点符号分隔的句子
    sentences = re.split(r'[.,!?](?!$)', in_str)

    # 获取输入中具有最高等级单词的句子，并按等级对关键字排序
    sentence, sorted_keywords = rank(sentences, script, substitutions)

    # 查找匹配的分解规则
    for keyword in sorted_keywords:
        comps, reassembly_rule = decompose(keyword, sentence, script)
        # 如果找到匹配的分解规则则中断
        if comps:
            response = reassemble(comps, reassembly_rule)
            # 对于某些关键字，生成一个额外的响应推送到内存堆栈
            if keyword in memory_inputs:
                generate_memory_response(sentence, script, memory_stack)
            break
    # 如果没有找到匹配的分解规则
    else:
        # 如果内存堆栈不为空，
        # 从内存堆栈弹出答案
        if memory_stack:
            response = memory_stack.pop()
        # 否则，给出通用答案
        else:
            response = generate_generic_response(script)

    response = prepare_response(response)
    return response

def generate_generic_response(script):
    """生成独立于用户输入的通用响应。

    参数
    ----------
    script : dict[]
        包含关键字和规则信息的 JSON 对象。

    返回
    -------
    response : str
        通用响应。

    """
    # '$' 是通用答案关键字
    comps, reassembly_rule = decompose('$', '$', script)
    return reassemble(comps, reassembly_rule)

def generate_memory_response(sentence, script, memory_stack):
    """为内存堆栈生成响应。

    参数
    ----------
    sentence : str
        当前要分解和重组的句子。
    script : dict[]
        包含关键字和规则信息的 JSON 对象。
    memory_stack : str[]
        当 `generate_memory_response` 被提示时生成的响应堆栈。

    """
    # '^' 是内存堆栈关键字
    mem_comps, mem_reassembly_rule = decompose('^', sentence, script)
    mem_response = reassemble(mem_comps, mem_reassembly_rule)
    memory_stack.append(mem_response)

def prepare_response(response):
    """在向用户显示之前处理程序的响应。

    参数
    ----------
    response : str
        要处理的字符串。

    返回
    -------
    response : str
        处理后的字符串。

    """
    response = clean_string(response)
    response += "\nYou: "
    return response

def clean_string(in_str):
    """从字符串中移除多余的字符。

    参数
    ----------
    in_str : str
        要清理的字符串。

    返回
    -------
    in_str : str
        清理后的字符串。

    """
    # 移除额外空白字符
    in_str = ' '.join(in_str.split())
    # 移除标点符号前的空白字符
    in_str = re.sub(r'\s([?.!"](?:\s|$))', r'\1', in_str)

    return in_str
