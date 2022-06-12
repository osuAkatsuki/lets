from typing import Dict, Union


def zingonify(d: Dict[str, Union[str, int]]) -> str:
    """
    Zingonifies a string
    :param d: input dict
    :return: zingonified dict as str
    """
    return '|'.join(f'{k}:{v}' for k, v in d.items())
