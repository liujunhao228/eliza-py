import json

from utils.rules import process_decomp_rules

def setup(general_script_path, script_path):
    """设置程序，加载 JSON 脚本。

    返回
    -------
    general_script : dict
        通用脚本，包含有关语言和标签的信息。
    script : dict[]
        自定义脚本，包含关键字、等级、分解和重组规则。
    memory_inputs : str[]
        提示生成添加到内存堆栈的额外响应的关键字数组。
    exit_inputs : str[]
        可用于退出程序的关键字数组。

    """
    # 加载脚本
    general_script = load_script(general_script_path)
    script = load_script(script_path)

    # 处理自定义脚本中的分解规则
    script = process_decomp_rules(script, general_script['tags'])

    # 获取程序执行所需的信息
    memory_inputs = general_script['memory_inputs']
    exit_inputs = general_script['exit_inputs']

    return general_script, script, memory_inputs, exit_inputs

def load_script(script_path):
    """从 JSON 文件加载脚本。

    参数
    ----------
    script_path : str
        JSON 文件的路径。

    返回
    -------
    script : dict or dict[]
        加载的 JSON 对象。

    """
    with open(script_path) as f:
        script = json.load(f)
    return script
