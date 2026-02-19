import os

from utils.startup import setup
from utils.rules import reset_all_last_used_reassembly_rule
from utils.response import prepare_response, generate_response

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
SCRIPT_DIR = os.path.join(PROJECT_DIR, 'scripts')
GENERAL_SCRIPT_PATH = os.path.join(SCRIPT_DIR, 'general.json')
SCRIPT_PATH = os.path.join(SCRIPT_DIR, 'doctor.json')


def main():
    memory_stack = []
    general_script, script, memory_inputs, exit_inputs = setup(GENERAL_SCRIPT_PATH, SCRIPT_PATH)

    # 获取第一个用户输入
    in_str = input("Eliza: 欢迎。\nYou: ")
    in_str_l = in_str.lower()

    # 主执行循环
    while in_str_l not in exit_inputs:

        # str.lower().islower() 是一种快速检查
        # 字符串是否包含任何字母字符的方法。
        # 来源：https://stackoverflow.com/a/59301031
        if not in_str_l.islower():
            response = prepare_response('Eliza: 请使用字母。毕竟我是人类。')
        elif in_str_l == 'reset':
            reset_all_last_used_reassembly_rule(script)
            response = prepare_response('Eliza: 重置完成。')
        else:
            response = generate_response(in_str, script, general_script['substitutions'], memory_stack, memory_inputs)

        # 获取下一个用户输入
        in_str = input(response)
        in_str_l = in_str.lower()

    print("Eliza: 再见。\n")

if __name__=="__main__":
   main()