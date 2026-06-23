# GitHub Collaboration Workflow

本项目已经有 GitHub 仓库后，推荐采用轻量流程，保证两天内能交付。

## 第一次连接远程仓库

本地仓库如果还没有 remote：

```bash
git remote add origin https://github.com/1am-not-sleep/NueroDEG.git
git fetch origin
```

切到你们已经创建好的测评分支：

```bash
git switch <测评分支名称>
```

如果本地没有该分支：

```bash
git switch -c <测评分支名称> origin/<测评分支名称>
```

## 日常协作

```bash
git status
git pull origin <测评分支名称>
```

完成一小块功能后：

```bash
git add .
git commit -m "feat: add neurodeg agent MVP"
git push origin <测评分支名称>
```

注意：提交和推送需要由项目成员明确确认后执行。

## 合并前检查

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests
python3 src/main.py data/example_neuro_deg.csv
```

网页演示：

```bash
streamlit run app.py
```

## 两天内优先级

P0:

- 命令行能跑
- Streamlit 页面能跑
- 示例数据能生成火山图和报告
- 缺列输入能报错

P1:

- README 完整
- 测试文件完整
- 知识库说明完整
- GitHub workflow 文件完整

P2:

- GSEApy / Enrichr
- PDF 导出
- PubMed 检索
- LLM API
