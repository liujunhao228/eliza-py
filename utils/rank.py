import re

def rank(sentences, script, substitutions):
    """根据脚本对关键字进行排名。
    仅返回具有最高等级关键字的句子。

    参数
    ----------
    sentences : str[]
        句子数组。

    script : dict[]
        包含不同关键字等级的 JSON 对象。

    substitutions : dict
        键值对，其中键 = 要替换的单词，值 = 新单词。

    返回
    -------
    sentences[max_index] : str
        `sentences` 中具有最高等级关键字的句子。
    sorted_keywords : str[]
        `sentences[max_index]` 中的单词根据其等级按降序排序。

    """
    all_keywords = []
    all_ranks = []
    maximums = []

    # 使用索引遍历，以便可以直接修改列表中的句子
    for i in range(0, len(sentences)):
        # 移除所有标点符号
        sentences[i] = re.sub(r'[#$%&()*+,-./:;<=>?@[\]^_{|}~]', '', sentences[i])
        # 替换关键字
        sentences[i] = substitute(sentences[i], substitutions)

        # 检查此时句子是否为空
        if sentences[i]:
            keywords = sentences[i].lower().split()
            all_keywords.append(keywords)

            # 获取此句子的等级
            ranks = get_ranks(keywords, script)

            # 追加此句子中的最高等级
            maximums.append(max(ranks))

            all_ranks.append(ranks)

    # 返回具有最高关键字等级的最早句子
    max_rank = max(maximums)
    max_index = maximums.index(max_rank)

    keywords = all_keywords[max_index]
    ranks = all_ranks[max_index]

    # 根据等级列表对关键字列表进行排序
    sorted_keywords = [x for _,x in sorted(zip(ranks, keywords), reverse=True)]

    return sentences[max_index], sorted_keywords

def get_ranks(keywords, script):
    """返回给定脚本中查询关键字的等级。

    参数
    ----------
    keywords : str[]
        要在脚本中搜索的关键字数组。
    script : dict[]
        包含不同关键字等级的 JSON 对象。

    返回
    -------
    ranks : int[]
        整数数组，顺序与其各自的关键字相同。

    """
    ranks = []

    # 填充等级列表
    for keyword in keywords:
        for d in script:
            if d['keyword'] == keyword:
                ranks.append(d['rank'])
                break
        # 如果没有为单词指定等级，则将其等级设置为 0
        else:
            ranks.append(0)

    return ranks

def substitute(in_str, substitutions):
    """根据字典替换字符串中的单词。

    参数
    ----------
    in_str : str
        要应用替换的字符串。
    substitutions : dict
        键值对，其中键 = 要替换的单词，值 = 新单词。

    返回
    -------
    out_str : str
        应用了相关替换的字符串。

    """
    out_str = ''

    # 遍历字符串中的所有单词
    for word in in_str.split():
        # 如果 substitutions 为此单词指定了替换，则替换它
        if word.lower() in substitutions:
            out_str += substitutions[word.lower()] + ' '
        # 否则保留相同的单词
        else:
            out_str += word + ' '

    return out_str
