"""资源层的通用操作：定位本地化对象、读取 / 写入文本字段。"""

import os
import struct

import UnityPy

# LocalizedStringAsset 是 Odin 序列化的 ScriptableObject，序列化时仍以 MonoBehaviour 存盘。
LOCALIZED_CLASS = "LocalizedStringAsset"
LOCALIZED_FULLNAME = "Library.Localization.LocalizedStringAsset"


def script_map(env, data_dir):
    """path_id -> 类名。MonoScript 统一放在 globalgamemanagers.assets 里。"""
    path = os.path.join(data_dir, "globalgamemanagers.assets")
    env_scripts = UnityPy.load(path)
    sf = next(iter(env_scripts.files.values()))
    out = {}
    for obj in sf.objects.values():
        if obj.type.name != "MonoScript":
            continue
        tree = obj.read_typetree()
        out[obj.path_id] = tree.get("m_ClassName")
    return out


def script_path_id(raw):
    """从 MonoBehaviour 原始字节里读 m_Script 的 path_id。

    布局：PPtr<GameObject> (12B) + m_Enabled (1B) + 3B 对齐 + PPtr<MonoScript> (fileID:int, pathID:long)。
    因此 fileID 在偏移 16，pathID 在偏移 20。UnityPy 在处理这种紧凑 PPtr 时
    有 3 字节偏移，这里直接按原始字节读取，避免踩坑。
    """
    if len(raw) < 28:
        return None
    return struct.unpack_from("<q", raw, 20)[0]


def load_serialized(path):
    env = UnityPy.load(path)
    return next(iter(env.files.values()))


def iter_localized(sf, scripts, nodes):
    """遍历文件里的 LocalizedStringAsset，产出 (object, typetree)。"""
    for obj in sf.objects.values():
        if obj.type.name != "MonoBehaviour":
            continue
        if scripts.get(script_path_id(obj.get_raw_data())) != LOCALIZED_CLASS:
            continue
        yield obj, obj.read_typetree(nodes)
