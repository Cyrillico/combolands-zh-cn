"""全局配置：路径、适用版本与校验值。

补丁是按某个具体构建版本制作的。Unity 的 .assets 与 DLL 一旦版本变化，
对象布局、字符串槽位都可能不同，硬套会破坏游戏文件。所以这里记录原版文件的
SHA-256，apply.py 会先比对，不匹配就拒绝执行（除非显式 --force）。
"""

import os

# 游戏默认安装路径，可用环境变量 COMBOLANDS_DIR 或命令行 --game-dir 覆盖
DEFAULT_GAME_DIR = os.environ.get(
    "COMBOLANDS_DIR", r"F:\SteamLibrary\steamapps\common\Combolands"
)

# 本补丁对应的 Steam 构建号（appid 4075620）
TARGET_BUILD = "25997697"
UNITY_VERSION = "6000.0.66f2"

DATA_DIR = "Combolands_Data"
MANAGED_SUBDIR = os.path.join(DATA_DIR, "Managed")

# 需要改写的文件（相对游戏根目录）
ASSET_FILES = [os.path.join(DATA_DIR, "resources.assets"),
               os.path.join(DATA_DIR, "sharedassets0.assets")]
DLL_FILE = os.path.join(MANAGED_SUBDIR, "Assembly-CSharp.dll")

# 原版文件校验值（build 25997697），用于版本守卫
EXPECTED_SHA256 = {
    os.path.join(DATA_DIR, "resources.assets"):
        "5bad16889b331ee2a1ec33f4f1ce31eb819e1d88caea5256d4cbfd900c145b04",
    os.path.join(DATA_DIR, "sharedassets0.assets"):
        "97a1597e540450071a695260103fce82584fca0434c98fe7ab69a62d86e5b44e",
    os.path.join(MANAGED_SUBDIR, "Assembly-CSharp.dll"):
        "31de0adac3f22f03c6f88195a629ee8d95b50d20450d9f32a53e0d428160f349",
}

# 中文字体资源：开启多图集，避免字形超出单张图集后显示方框
MULTI_ATLAS_FONTS = ["NotoSans-Bold SDF", "NotoSansSC-Bold SDF"]
