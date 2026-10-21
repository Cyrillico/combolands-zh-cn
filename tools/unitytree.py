"""由程序集生成 Unity 类型树，供 UnityPy 读取 MonoBehaviour 字段。

Unity 打包后的 .assets 默认不内嵌 TypeTree，UnityPy 只能拿到原始字节。
游戏的 Assembly-CSharp.dll 里保留了完整的类定义，用 TypeTreeGeneratorAPI
把它转成 TypeTree 后，就能按字段名读写这些脚本对象。
"""

import glob
import os

from TypeTreeGeneratorAPI import TypeTreeGenerator


class Trees:
    """加载 Managed 目录下所有 DLL，并按类型名生成 UnityPy 可用的节点树。"""

    def __init__(self, managed_dir, unity_version):
        self.generator = TypeTreeGenerator(unity_version)
        for dll in glob.glob(os.path.join(managed_dir, "*.dll")):
            try:
                with open(dll, "rb") as f:
                    self.generator.load_dll(f.read())
            except Exception:
                # 依赖缺失或加密的程序集跳过即可，不影响目标类型
                continue
        self._cache = {}

    def nodes(self, fullname, assembly="Assembly-CSharp.dll"):
        """返回形如 [{m_Level, m_Type, m_Name, m_MetaFlag, ...}] 的节点列表。"""
        if fullname in self._cache:
            return self._cache[fullname]
        raw = self.generator.get_nodes(assembly, fullname)
        out = [
            {
                "m_Level": n.m_Level,
                "m_Type": n.m_Type,
                "m_Name": n.m_Name,
                "m_MetaFlag": n.m_MetaFlag,
                "m_ByteSize": 0,
                "m_TypeFlags": 0,
                "m_Version": 1,
            }
            for n in raw
        ]
        self._cache[fullname] = out
        return out
