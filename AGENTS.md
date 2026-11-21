# AGENTS.md

给协作者（人和 AI）的项目约定。违反以下任一条的输出都应被拒绝。

## 项目定位

个人学习 SPE *Fundamentals of Drilling Engineering*（Mitchell & Miska, 2011）的计算与笔记仓库。
第一位是**自己的计算、推导、练习**；公开与展示是副产品。
**本仓库只做通用钻井工程内容，不引入柔性钻具/多体动力学。**

## 铁律

### 1. 版权
- 只写自己的推导、复述、代码和自造算例。
- **禁止**搬运原书段落、原书图表、课后题原题（题号可内部索引，题干必须改写）。
- 中文教材同理。

### 2. 保密
- 数据只允许出现：地层名称、顶底深度、压力系数、Biot 系数、泊松比、粘聚力、内摩擦角、密度。
- **禁止**出现：井号、X/Y 坐标、补心海拔、完井深度、客户名称、任何本地绝对路径。
- 引用外部来源时在文中注明出处；参数一律标注"示例设计取值，非实测"。

### 3. 单位
- 代码内部一律 SI：Pa、m、kg/m³、N、s。
- 现场单位（ppg、psi、lbf、ft、gal）只允许出现在 `drilleng.py` 的换算函数与文档表格里。
- 禁止在计算函数内部硬编码 `0.00981`、`0.05195` 之类的混合单位系数。

### 4. 语言与命名
- 正文中文；章节标题、README、代码注释用英文或中英并列。
- 术语首次出现时中英并列：`井壁稳定 (wellbore stability)`。
- 文件名全 ASCII。

### 5. 代码组织
- 计算页用 marimo `.py`，文件头必须有 PEP 723 依赖声明。
- 描述页用 `.md`。
- 复用的物理/数值函数放根目录 `drilleng.py`，单文件、**硬上限 300 行**、不建包、不引入 pytest。
- 公式推导写在 notebook 的 Markdown cell 里；`drilleng.py` 只放已验证的实现。

### 6. 禁止的"调参式修补"
不允许为了让图好看而给物理量加人为上下限（如 `pc = min(pc, 0.95*pf)`）。
如果模型给出的结果不合理，正确做法是**在正文里说明假设的局限**，而不是夹逼数值。

## 目录约定

```
drilleng.py                 公共函数 + 末尾 _self_test()
NN-topic-slug.py            marimo 计算页（唯一源文件）
NN-topic-slug.md            描述页
NN-topic-slug.ipynb         生成物：让 GitHub 能直接渲染带输出的 notebook
data/*.csv                  清洗后的输入数据（UTF-8，无 BOM）
figures/*.png               成品图，由 notebook 生成
__marimo__/session/         生成物：执行快照，供 molab 预览
```

**生成物只生成、不手改**：`*.ipynb`、`figures/*.png`、`__marimo__/session/*` 一律由命令重建。

## 一个主题"算完成"的标准

1. 一页自己的话推导（无原文搬运）
2. `drilleng.py` 有对应函数，`_self_test()` 通过
3. notebook 能一键重算并出图
4. 一张可放进简历的成品图，存到 `figures/`
5. README 的目录表里加一行 + molab 交互链接
6. `__marimo__/` 快照已提交

## 常用命令

```bash
uv run drilleng.py                                  # 跑自测
uvx marimo edit 02-rock-mechanics.py                # 编辑
uvx marimo export session --sandbox 02-rock-mechanics.py     # 刷新 molab 预览快照
uvx --with nbformat marimo export ipynb 02-rock-mechanics.py \
    -o 02-rock-mechanics.ipynb --sandbox --include-outputs   # 刷新 GitHub 可渲染副本
```

## 提交前检查清单

- [ ] 没有原书原文/原图
- [ ] 没有井号、坐标、客户名、本地路径
- [ ] 没有 field-unit 魔数混进计算函数
- [ ] `uv run drilleng.py` 自测通过
- [ ] `figures/*.png`、`*.ipynb`、`__marimo__/session/` 三样生成物都已重建
