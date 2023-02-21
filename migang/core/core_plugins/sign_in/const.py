from pathlib import Path

SIGN_RESOURCE_PATH = Path(__file__).parent / "res"
SIGN_BORDER_PATH = SIGN_RESOURCE_PATH / "border"
SIGN_BACKGROUND_PATH = SIGN_RESOURCE_PATH / "background"

lik2relation = {
    "0": "路人",
    "1": "陌生",
    "2": "初识",
    "3": "普通",
    "4": "友好",
    "5": "熟知",
    "6": "默契",
    "7": "陪伴",
    "8": "比翼",
}

level2attitude = {
    "0": "排斥",
    "1": "警惕",
    "2": "可以交流",
    "3": "一般",
    "4": "是个好人",
    "5": "好朋友",
    "6": "可以分享小秘密",
    "7": "超级信任",
    "8": "嘻嘻",
}


lik2level = {
    0: "0",
    12: "1",
    25: "2",
    70: "3",
    200: "4",
    680: "5",
    1350: "6",
    2500: "7",
    12060: "8",
}
