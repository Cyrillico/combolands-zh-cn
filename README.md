# Combolands 简体中文补丁

给 Steam 游戏 **Combolands: Roguelike Citybuilder**（appid 4075620）做的简体中文汉化，以「脚本 + 译文表」的形式发布。

> **仓库里没有任何游戏文件。** 你需要自己拥有正版游戏，脚本会在本地读取你的游戏文件、写入中文，再覆盖回去。

当前适配版本：Steam build `25997697`（2026-10-21 更新）

- 译文覆盖：1,090 条本地化文本中的 **1,083 条**（其余 7 条是 `[MoneyCount]` 之类的纯占位符，不需要翻译）
- 另有 11 条编译进 `Assembly-CSharp.dll` 的教程/提示文本
- 字体：游戏自带 `NotoSansSC-Bold SDF` 并挂在正文 `NotoSans-Bold SDF` 的回退链上，脚本会把这两个字体资源设为多图集，**不需要 BepInEx / XUnity**

## 快速开始

```bash
pip install -r requirements.txt

# 预览生成到 ./out，不动游戏
python tools/apply.py --game-dir "F:\SteamLibrary\steamapps\common\Combolands"

# 确认没问题后直接安装（会先把原文件备份到游戏目录旁边）
python tools/apply.py --game-dir "F:\SteamLibrary\steamapps\common\Combolands" --install
```

`--game-dir` 指向 `Combolands.exe` 所在目录；也可以设环境变量 `COMBOLANDS_DIR`。

还原：把备份目录里的 3 个文件复制回去，或在 Steam 里「验证游戏文件完整性」。

## 原理

游戏的界面文本不是明文表，而是每个词条一个 `LocalizedStringAsset`（Odin 序列化的 ScriptableObject，存盘时仍是 MonoBehaviour），字段如下：

| 字段 | 含义 |
| --- | --- |
| `Key` | 词条键，如 `Building.Apiary.Description` |
| `_originalString` | 实际显示的文本 |
| `_explanationText` | 补充说明 |

补丁只改 `_originalString`。

难点在于打包后的 `.assets` 不带 TypeTree，UnityPy 读不出字段。这里用 `TypeTreeGeneratorAPI` 从游戏的 `Assembly-CSharp.dll` 反推类型树，再交给 UnityPy 按字段名读写——读取后原样写回是**字节级无损**的，所以可以放心只动目标字段。

教程文本不在资源里，而是编译进 DLL 的 `#US` 字符串堆。这部分做等长替换：保持长度前缀的字节宽度、写入新长度与中文、剩余字节补零，文件大小完全不变，字符串偏移不移动。

## 校验

```bash
python tools/verify.py --game-dir "F:\...\Combolands" --out ./out
```

脚本会逐对象比对原版与补丁：对象数量必须一致，改动的对象必须都在译文表里，未改动对象必须逐字节相同，DLL 大小必须不变。v7 的结果：

| 项目 | 结果 |
| --- | --- |
| `resources.assets` | 5,037 个对象，改 991 个，意外改动 0 |
| `sharedassets0.assets` | 1,016 个对象，改 92 个 + 2 个字体资源，意外改动 0 |
| `Assembly-CSharp.dll` | 944,128 字节不变，11 条文本，槽位外 0 字节 |

`docs/text_audit.html` 是可搜索的中英对照页，`docs/validation.json` 是结构化结果。

## 版本守卫

补丁绑定具体构建。`config.py` 里记录了原版三个文件的 SHA-256，`apply.py` 会先比对；游戏更新后哈希对不上会直接拒绝执行，避免把旧资源硬套到新版本上（这会破坏游戏）。

确实想试新版本时：

```bash
python tools/extract.py --game-dir "F:\...\Combolands" --out current_strings.json   # 导出新版本条目
```

然后用 `Key` 对齐、以旧译文为基础补译，再 `apply.py --force`。

## 目录

```
config.py                 版本、路径、原版哈希
tools/
  unitytree.py            从 DLL 生成 Unity 类型树
  gameassets.py           定位 LocalizedStringAsset、读写字段
  extract.py              导出全部词条
  apply.py                注入译文并生成补丁
  dll_patch.py            DLL 字符串堆等长替换
  verify.py               对象级校验
translations/
  translations.json       Key -> 中文（1,083 条）
  dll_strings.json        DLL 教程文本 11 条
docs/
  text_audit.html         中英对照审查页
  validation.json         校验结果
```

## 已知限制

- 未逐条实机验收。发现错译、空白、截断或方框，欢迎提 issue 并附截图和所在界面。
- 游戏按空白字符切分说明文本，每个分段只解析第一个 `[]` 标记，因此译文在标记两侧保留了空格，看起来松散但不是漏字。
- 数字、图标由游戏运行时填充，没有写死数值。
- 动态拼接的短语可能仍残留英文片段。

## 版权

游戏及其全部内容的版权归 Crux Games 所有。本仓库只包含翻译文本和工具脚本，不包含任何游戏资源、代码或可执行文件，使用时必须自备正版游戏。译文属同人作品，仅供交流学习；如权利方认为不妥，请提 issue，会立即移除相关内容。
