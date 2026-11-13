# 复现 SkillShiftBench教程

- conversation_id: `6af3e10a-0d7c-83ea-95e9-17897fb0961e`
- create_time: 1794367754.377866
- update_time: 1794393055.397468
- exported_at: 2026-11-11T10:38:28.998Z

## 深度思考

- Searching the web
- Searching SkillShiftBench skillshift-bench github reproduction dataset setup
- Searching SkillShiftBench benchmark github Zhang Shuyi
- Searching 12 websites
- Searching Docker Desktop WSL 2 backend install Windows enable WSL integration settings official docs
- Searching Microsoft WSL move project files Windows filesystem to Linux filesystem performance /mnt/c official docs
- Searching Docker Desktop WSL 2 docker volumes stored Linux filesystem best practices official
- Searching 3 websites
- Searching Ubuntu 24.04 systemd-binfmt.service failed WSL python3-venv apt triggers
- Searching 7 websites
- Searching github SkillShift-Bench skillshift-bench evaluator deterministic success evaluator run report
- Searching 5 websites
- Searching SkillShift Bench paper skill learning source tasks evaluation src src-perc src-exec tgt transfer protocol AWM ASI SkillWeaver WALT
- Searching SkillShift Bench arxiv 2610.33528 pdf experiments transfer diagnostics table 1
- Searching 11 websites
- Searching github SkillShift-Bench skillshift-bench docs tasks perturbations condition src-perc src-exec evaluator reference agent baselines mpcr
- Searching SkillShift-Bench paper skill freeze ASI MPCR benchmark five changes source perception execution metrics
- Searching github SkillShift-Bench skillshift-envs setup conditions src-perc exec perturbations
- Searching 16 websites
- Searching github SkillShift-Bench skillshift-bench execution_shift.py perceptual_shift.py run outputs trace artifacts per_task.jsonl
- Searching 13 websites
- Searching 14 websites
- Searching SkillShift Bench my_api_key my_base_url my_model reference agent configuration
- Searching 火山方舟 deepseek-v4-1-flash-economy-261017 model id ark api v3
- Searching github SkillShift-Bench skillshift-bench reference agent my_model
- Searching 2 websites
- Searching github SkillShift-Bench skillshift-bench src skillshift tasks instance.py SHOPPING_ADMIN_V1 environment variables
- Searching SkillShift Bench configuration SHOPPING_ADMIN_V1 GITLAB_V1 setup environment
- Searching github SkillShift-Bench skillshift-bench reference agent action markdown code fence extract
- Searching github SkillShift-Bench skillshift-bench src skillshift agents reference.py
- Searching 10 websites
- Searching github SkillShift-Bench skillshift-bench reference.py extract_action _FENCE_RE
- Searching github SkillShift-Bench skillshift-bench reference.py extract_action
- Searching 6 websites

## 用户

我需要复现 shuyi@DESKTOP-7HNQ7U2:/mnt/d/projects/zhangshuyi/SkillShiftBench/skillshift-bench$
请从数据,环境等等环节,依次告诉我如何实现

## ChatGPT

我会按“确认项目版本 → 准备数据 → 配置 WSL/Linux 环境 → 安装依赖 → 运行基线 → 复现实验结果 → 排查问题”的顺序整理。先核对 SkillShiftBench 的公开仓库和运行说明，避免给你不适用的安装命令。

## 深度思考

Searched 12 websites

## ChatGPT

# SkillShift-Bench 完整复现教程：从数据、环境到实验结果

我已经找到 SkillShift-Bench 的官方代码仓库、环境仓库和复现文档。下面按照你的 **Windows + WSL2 + Ubuntu** 环境，给你一套可以逐步执行的复现流程。

你现在的位置是：

```bash
shuyi@DESKTOP-7HNQ7U2:/mnt/d/projects/zhangshuyi/SkillShiftBench/skillshift-bench$
```

这说明你已经进入了 WSL/Linux 终端，并且位于项目代码目录。**我们从这里继续，不需要重新安装 WSL，也不需要重复克隆已有的项目。**

## 一、首先明确我们要复现什么

论文：<Entity category="book" value="SkillShift-Bench: Benchmarking Skill Learning under Environment Evolution for Web Agents"/>

官方资源：

- <Link url="https://github.com/SkillShift-Bench/skillshift-bench" title="Benchmark 代码仓库"/>
- <Link url="https://github.com/SkillShift-Bench/skillshift-envs" title="网站环境仓库"/>
- <Link url="https://skillshift-bench.github.io/docs/quickstart/" title="官方复现文档"/>
- <Link url="https://arxiv.org/abs/2610.33528" title="论文原文"/>

SkillShift-Bench 用于评估：当网站环境发生变化时，Web Agent 之前学到的技能能否继续完成任务。

它包括三个网站和六种实验条件。

| 网站 | 任务族数量 |
|---|---:|
| GitLab | 162 |
| Magento | 114 |
| WordPress | 79 |
| **总计** | **355** |

每个任务族有六种环境条件：

| 条件 | 含义 |
|---|---|
| `src` | 原始环境 |
| `src-perc` | 原始环境 + 感知变化 |
| `src-exec` | 原始环境 + 执行障碍 |
| `tgt` | 更新后的网站环境 |
| `tgt-perc` | 更新环境 + 感知变化 |
| `tgt-exec` | 更新环境 + 执行障碍 |

这些是官方 Benchmark 的实验设计。<Cite refs={["turn788551view0","turn448540academia18"]}/>

## 二、整体复现路线

<box border radius="xl" padding={3} gap={3}>
  <list connector="solid" marker="number" gap={2}>
    <list-item>**检查现有代码和系统**

      确认仓库、Python、WSL、Docker 是否正常。
    </list-item>
    <list-item>**准备实验数据**

      检查任务文件、任务 ID、实验配置和测试数据。
    </list-item>
    <list-item>**建立 Python 环境**

      创建独立虚拟环境，安装项目和 Playwright。
    </list-item>
    <list-item>**搭建网站环境**

      使用 Docker 启动 GitLab，再扩展到 Magento 和 WordPress。
    </list-item>
    <list-item>**配置大模型**

      配置 API Key、模型名称和 API 地址。
    </list-item>
    <list-item>**运行最小测试**

      先执行一个 GitLab 任务，检查完整链路。
    </list-item>
    <list-item>**复现论文实验**

      运行不同 Agent、不同网站、不同环境条件。
    </list-item>
    <list-item>**计算指标、对比论文**

      生成 Success Rate 等指标，整理实验表格。
    </list-item>
  </list>
</box>

**建议先实现一个 GitLab `src` 任务的完整运行，再逐渐扩展。** 不要一开始就运行全部任务，否则 Docker、网站初始化、模型 API 或 Agent 配置中的任何问题都会让调试非常困难。

## 三、第一步：检查 WSL 和项目环境

先不要安装任何东西。

在你当前终端执行：

```bash
pwd
ls -la
git status --short
git rev-parse HEAD
```

预期 `pwd` 输出：

```text
/mnt/d/projects/zhangshuyi/SkillShiftBench/skillshift-bench
```

`ls` 应能看到以下关键目录或文件：

```text
skillshift-bench/
├── data/
├── docs/
├── examples/
├── scripts/
├── src/
├── tests/
├── pyproject.toml
├── requirements-lock.txt
└── README.md
```

再检查系统和工具：

```bash
uname -m
cat /etc/os-release
python3 --version
git --version
docker --version
docker compose version
docker info
```

重点是：

- `uname -m` 最好为 `x86_64`，因为官方网站镜像需要 AMD64 架构。
- Python 必须能运行。
- Docker 服务必须正常，`docker info` 不能报连接 daemon 失败。
- WSL2 必须能访问 Docker。

若你尚未配置 Docker，推荐在 Windows 安装 Docker Desktop，启用 WSL2 backend，并在 Docker Desktop 的 Settings → Resources → WSL Integration 中开启对应的 Ubuntu 发行版。

另外，你现在把仓库放在 `/mnt/d/...` 下，这是 Windows D 盘映射路径。代码可以在这里运行，但 Docker 数据库和大量小文件操作可能变慢。建议在遇到 I/O 性能问题时，把项目和环境移到 WSL 的 Linux 文件系统，例如 `~/projects/SkillShiftBench/`。尤其不要把 GitLab 的数据库持久化目录随意放在 Windows 挂载盘上。

## 四、第二步：检查和准备任务数据

这里要区分两类数据：

**第一类：Benchmark 任务数据**，通常随 `skillshift-bench` 代码仓库发布。

**第二类：网站状态数据**，包含 GitLab、Magento、WordPress 的数据库、网站文件、测试账号及预置业务对象，需要由环境仓库及备份恢复。

这两部分都准备好，才能进行真实实验。

### 4.1 检查任务数据

保持在 `skillshift-bench` 根目录：

```bash
ls -lah data
find data -maxdepth 3 -type f | sort | head -80
```

查看任务 ID 映射：

```bash
head -n 10 data/tasks/id_map.csv
```

查看校准任务集：

```bash
python3 -m json.tool data/calibration_set.json | head -60
```

还可以检查仓库中的任务文件数量和结构：

```bash
find data/tasks -type f | sort
```

注意：355 是任务族数量，不一定等于目录中的 JSON 文件数。GitLab 和 Magento 的 source/target 任务可能分别存储，而 WordPress 使用单份任务文件。具体以你的代码版本为准。

### 4.2 获取网站数据

官方环境备份地址：

<Link url="https://huggingface.co/chenboyu/website_data" title="Hugging Face：chenboyu/website_data"/>

根据官方环境文档，各站点版本和备份关系如下。<Cite refs={["turn218458view0","turn412559view0"]}/>

| 网站 | Source | Target |
|---|---|---|
| GitLab | 12.0.0 | 16.0.6 |
| Magento | 1.9 | 2.4 |
| WordPress | news-portal 主题 | twentytwentyfour 主题 |

目前官方环境文档说明预构建镜像尚未全部发布，推荐通过 `--from-hf` 从备份重建环境。Magento 2.4 还需要 WebArena 的镜像文件。

**因此，不要直接下载一个最新版 GitLab 镜像来代替。版本不一致会导致任务行为和论文实验不一致。**

## 五、第三步：创建独立 Python 环境

回到根目录：

```bash
cd /mnt/d/projects/zhangshuyi/SkillShiftBench/skillshift-bench
```

检查项目规定的 Python 要求：

```bash
grep -n -A 8 'requires-python' pyproject.toml
```

如果当前 Python 版本满足要求，推荐使用 `venv` 建立独立环境：

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
```

之后检查：

```bash
which python
python --version
```

正常情况下 `which python` 会指向：

```text
.../skillshift-bench/.venv/bin/python
```

安装项目：

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[run]"
```

如果后面准备复现 MPCR，包括其可选 embedding 检索依赖，可以使用：

```bash
python -m pip install -e ".[run,mpcr]"
```

官方仓库还提供 `requirements-lock.txt`，用于记录实验依赖版本。若目标是严格复现论文而不是先跑通代码，应核对锁定版本，并避免随意升级依赖。<Cite refs={["turn412559view0","turn808386view0"]}/>

### 5.1 安装 Playwright 浏览器

```bash
python -m playwright install chromium
```

如果系统依赖缺失，在 Ubuntu 下可执行：

```bash
sudo .venv/bin/python -m playwright install-deps chromium
```

### 5.2 检查安装是否成功

```bash
python -c "import skillshift; print('skillshift import OK')"
skillshift --help
```

然后运行不需要 Docker、GPU 或模型 API Key 的官方 Smoke Test：

```bash
python scripts/smoke_test.py
```

如果测试通过，说明基础 Python 代码和依赖至少已经能够正常加载。

此时还不能说明网站环境已经部署成功。

## 六、第四步：搭建 GitLab 网站环境

这是复现中最容易出现问题的环节。

官方把网站环境放在独立仓库 `skillshift-envs` 中，建议把它放在 `skillshift-bench` 的同级目录。

### 6.1 下载环境仓库

在当前目录执行：

```bash
cd ..
git clone https://github.com/SkillShift-Bench/skillshift-envs.git
```

此时目录应该类似：

```text
SkillShiftBench/
├── skillshift-bench/
│   ├── .venv/
│   ├── data/
│   ├── src/
│   └── ...
└── skillshift-envs/
    ├── compose/
    ├── configs/
    ├── images/
    ├── scripts/
    └── setup.sh
```

如果你已经有 `skillshift-envs`，不要再次克隆，直接进入它：

```bash
cd skillshift-envs
```

### 6.2 先查看部署命令

```bash
./setup.sh --site gitlab --condition src --dry-run
```

这个命令会打印准备执行的操作，但不真正部署。

重点观察镜像下载、数据恢复、Docker Compose 文件和端口。

### 6.3 从官方备份部署 GitLab 12.0

```bash
./setup.sh --site gitlab --condition src --from-hf
```

该路径按照官方文档从 Hugging Face 获取备份并重建对应环境。需要足够的可用磁盘空间，也要保证能正常访问 Hugging Face。<Cite ref="turn218458view0"/>

注意：首次恢复 GitLab 需要初始化多个内部服务，启动较慢是正常现象，但不能单凭容器处于 Running 状态就判定网站可用。

### 6.4 检查 GitLab

在环境仓库中：

```bash
docker ps -a
curl -I http://localhost:8080/users/sign_in
```

再回到 Benchmark：

```bash
cd ../skillshift-bench
source .venv/bin/activate
export GITLAB_V1=http://localhost:8080
skillshift env status
```

预期检查结果至少要满足：

- GitLab 可通过 `localhost:8080` 访问。
- 环境检查报告 GitLab 正常。
- 检测版本为 12.0.0，而不是其他版本。

可以在 Windows 浏览器访问：

<Link url="http://localhost:8080" title="本地 GitLab 地址"/>

如果 Windows 浏览器无法打开，但 WSL 中的 `curl` 可以正常访问，需要进一步检查 Docker 端口映射和 WSL 网络转发。

### 6.5 再准备目标环境 GitLab 16.0

在 Source 环境能运行之后，再执行：

```bash
cd ../skillshift-envs
./setup.sh --site gitlab --condition tgt --from-hf
```

并在 Benchmark 中设置：

```bash
cd ../skillshift-bench
source .venv/bin/activate

export GITLAB_V1=http://localhost:8080
export GITLAB_V2=http://localhost:8081

skillshift env status
```

官方使用的 GitLab 端口：

| 版本 | HTTP 端口 |
|---|---:|
| GitLab 12 | 8080 |
| GitLab 16 | 8081 |

当两个版本都正确运行后，才具备进行 GitLab source/target 对比的基础。

## 七、第五步：配置模型 API

官方内置了 `reference` Agent，供环境连通性检查和基准测试使用。

官方 Quickstart 使用以下环境变量：

```bash
export my_api_key="你的API_KEY"
export my_base_url="你的模型API地址"
export my_model="你的模型名称"
```

具体取值取决于你的模型服务商。例如，使用 OpenAI 兼容接口时，需要提供相应的 API 地址和模型 ID。

为了避免将 Key 写入项目代码，建议在当前终端临时设置变量，或者使用不提交到 Git 的本地配置文件。

检查是否设置成功（不要打印完整密钥）：

```bash
python - <<'PY'
import os

for key in ["my_api_key", "my_base_url", "my_model"]:
    value = os.getenv(key)
    print(f"{key}: {'configured' if value else 'MISSING'}")
PY
```

**注意：** 模型选择会影响成功率。要严格复现论文表格，应使用与原始实验一致的模型、提示词、temperature、最大步数和 Agent 实现，而不能任意替换模型。

## 八、第六步：先运行一个 GitLab 任务

确保当前所在位置：

```bash
cd /mnt/d/projects/zhangshuyi/SkillShiftBench/skillshift-bench
source .venv/bin/activate
```

确认 GitLab 可访问：

```bash
skillshift env status
```

运行官方最小示例：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.v1.0 \
  --out runs/first
```

这条命令会：

1. 加载 GitLab 的指定任务。
2. 创建 `reference` Agent。
3. 连接本地 GitLab。
4. 通过浏览器执行操作。
5. 由 Benchmark 评估任务。
6. 将结果保存到 `runs/first`。

这是非常重要的里程碑。

**只要这一步能够完整执行并得到有效的任务评估记录，即使任务没有成功，你的基础复现链路也已经基本打通。**

## 九、第七步：复现 MPCR 或其他方法

这里有一个必须说明的限制。

根据官方 Baselines 文档，论文中比较的 AWM、ASI、SkillWeaver 和 WALT 的实验版本没有在 Benchmark 仓库中完整发布。

但官方已经发布：

- MPCR 的实现：`src/skillshift/agents/mpcr/`
- MPCR 的消融变体
- ASI 与 MPCR 共享的冻结技能库

因此，**使用官方仓库复现 MPCR 比从零严格复现四个基线方法更现实**。想精确复现 AWM、ASI、SkillWeaver、WALT，仍需整合其上游代码并处理原始实验配置缺失的问题。<Cite ref="turn218458view1"/>

先查看 MPCR 的具体实现和运行接口：

```bash
ls -lah src/skillshift/agents/mpcr

grep -R -n "mpcr" \
  docs/ examples/ README.md | head -60

skillshift run --help
```

对于需要自行接入的方法，官方提供 `reset` 和 `act` 两个接口，Agent 可以通过 `module:Factory` 形式传给运行器。

建议先运行官方提供的 `reference`，然后再接入 MPCR，而不是一开始就尝试改写实验代码。

## 十、第八步：扩展到所有环境条件

在 GitLab Source 成功运行后，可按以下顺序扩展：

```bash
# Source 原始环境
skillshift run --agent reference \
  --site gitlab --condition src \
  --out runs/gitlab-src

# Source 感知变化
skillshift run --agent reference \
  --site gitlab --condition src-perc \
  --out runs/gitlab-src-perc

# Source 执行障碍
skillshift run --agent reference \
  --site gitlab --condition src-exec \
  --out runs/gitlab-src-exec

# Target 新环境
skillshift run --agent reference \
  --site gitlab --condition tgt \
  --out runs/gitlab-tgt
```

之后还需要运行 `tgt-perc` 和 `tgt-exec`。

这里使用 `reference` 只是验证运行流程，**并不是在复现论文中的 MPCR 或 ASI 成绩**。

准备好全部三个网站和六种环境后，可以对已接入的 Agent 执行：

```bash
skillshift run \
  --agent your_module:Factory \
  --all \
  --out runs/full
```

全量执行包括 2,130 个任务实例，因此必须提前评估 API 成本、时间和机器资源。<Cite ref="turn218458view2"/>

## 十一、第九步：生成实验指标

官方支持生成结果报告：

```bash
skillshift report runs/gitlab-src \
  --out submission/gitlab-src/ \
  --name "Reference ReAct" \
  --model "$my_model"
```

然后验证：

```bash
skillshift validate submission/gitlab-src/results.json
```

但要注意，官方 leaderboard 对任务覆盖量有要求。如果只执行了一个任务，报告即使可以生成，也不能视为完整 Benchmark 提交结果。

主要指标包括：

| 指标 | 含义 |
|---|---|
| SR | Success Rate，任务成功率 |
| AS | Average Steps，平均执行步数 |
| ASC | Average Skill Calls，平均技能调用数 |
| SFR | Skill Failure Rate，技能调用失败率 |

正式比较时，需要保证 Agent、任务集、模型和评估条件一致。

## 十二、复现论文结果时需要注意的两个限制

**第一，官方校准基准暂未完整发布。**

虽然项目提供：

```bash
skillshift calibrate
```

但目前官方文档明确说明：用于比对环境正确性的校准参考结果尚未发布，因此该命令可能以退出码 `2` 结束。这不一定代表本地安装失败。<Cite ref="turn218458view3"/>

你可以先执行：

```bash
skillshift calibrate --dry-run
```

检查校准计划，不需要立即运行完整校准。

**第二，复现执行流程不等于严格复现论文成绩。**

论文中的部分方法缺少精确版本、完整集成和任务级结果记录。即使你成功运行所有任务，得到的 SR 也可能与论文不同，需要记录代码 commit、模型版本、网站镜像和实验参数。

---

## 十三、你现在应该先执行什么？

目前我们已经有一套完整路线，但还不知道你本地实际安装到了哪一步。

建议先完成 **第一阶段：环境检查、任务数据检查、Python 基础验证**。现在不要急着下载 GitLab 大型备份。

在你当前终端直接复制下面这一整段：

<box gap={2}>
  <row align="center" justify="between">
    **第一阶段：环境诊断命令**
    <button size="sm" color="secondary" variant="outline" onClick={() => GenUI.copy("pwd\nuname -m\ncat /etc/os-release | head -6\npython3 --version\ngit rev-parse --short HEAD\ndocker --version\ndocker compose version\ndocker info --format '{{.ServerVersion}}'\nls -lah\nls -lah data\nfind data/tasks -maxdepth 2 -type f | head -20\nls -d ../skillshift-envs 2>/dev/null || true")}>
      <icon name="copy" size="xs"/> 复制
    </button>
  </row>
  <CodeBlock language="bash">pwd
uname -m
cat /etc/os-release | head -6
python3 --version
git rev-parse --short HEAD

docker --version
docker compose version
docker info --format '{{.ServerVersion}}'

ls -lah
ls -lah data
find data/tasks -maxdepth 2 -type f | head -20
ls -d ../skillshift-envs 2>/dev/null || true</CodeBlock>
</box>

把这段命令的**完整输出结果**发给我。

我就能根据你的真实 WSL 系统、Python 版本、Docker 状态和已有数据，继续按步骤指导你：哪些环节已经完成、哪些可以跳过，以及下一条具体该运行什么命令，直到 GitLab 第一个实验成功运行。

## 用户

没有安装docker:
(base) shuyi@DESKTOP-7HNQ7U2:/mnt/d/projects/zhangshuyi/SkillShiftBench/skillshift-bench$ docker --version\
\
The command 'docker' could not be found in this WSL 2 distro.\
We recommend to activate the WSL integration in Docker Desktop settings.\
\
For details about using Docker Desktop with WSL 2, visit:\
\
https\://docs.docker.com/go/wsl2/
现在我准备按照建议：配置 Docker，推荐在 Windows 安装 Docker Desktop，启用 WSL2 backend，并在 Docker Desktop 的 Settings → Resources → WSL Integration 中开启对应的 Ubuntu 发行版。

此外，如何实现你的提示：现在把仓库放在 `/mnt/d/...` 下，这是 Windows D 盘映射路径。代码可以在这里运行，但 Docker 数据库和大量小文件操作可能变慢。建议在遇到 I/O 性能问题时，把项目和环境移到 WSL 的 Linux 文件系统，例如 `~/projects/SkillShiftBench/`。尤其不要把 GitLab 的数据库持久化目录随意放在 Windows 挂载盘上。

## ChatGPT

我会把这一步拆成两部分：先在 Windows 安装并连通 Docker Desktop 与 WSL2，再把项目从 `/mnt/d` 迁移到 Ubuntu 自己的 Linux 文件系统。迁移时保留原目录作为备份，并检查 Docker 数据卷不会落在 Windows 挂载盘上。

## 深度思考

Searched 3 websites

## ChatGPT

你现在的情况很清楚：

- Windows 已经安装并使用 WSL2。
- 你正在 WSL 的 Ubuntu 终端中工作。
- Docker Desktop 尚未配置好，Ubuntu 无法使用 `docker`。
- 项目位于 Windows D 盘的 `/mnt/d/projects/...`。
- 你希望把 SkillShift-Bench 搬到 WSL 的 Linux 文件系统，避免之后部署 GitLab、Magento、WordPress 时产生性能问题。

**推荐方案：Windows 安装 Docker Desktop，使用 WSL2 引擎；把 SkillShift-Bench 项目放在 Ubuntu 的 `/home/shuyi/projects/` 下；Docker 数据用 Linux 命名卷管理。**

下面按照顺序操作。

# 第一部分：在 Windows 安装 Docker Desktop

## 第 1 步：确认 WSL 版本

先打开 Windows 的 **PowerShell**，不是 Ubuntu 终端，执行：

```powershell
wsl --version
wsl -l -v
```

正常情况下，第二条命令的结果类似：

```text
  NAME            STATE           VERSION
* Ubuntu-22.04    Running         2
  docker-desktop  Stopped         2
```

你的 Ubuntu 名称可能是 `Ubuntu`、`Ubuntu-22.04` 或 `Ubuntu-24.04`，以实际输出为准。

关键是 `VERSION` 必须等于 `2`。

如果不是，先执行（替换成实际发行版名称）：

```powershell
wsl --set-version Ubuntu-22.04 2
```

建议更新 WSL：

```powershell
wsl --update
```

更新后如果系统提示重新启动，就先重新启动 Windows。

## 第 2 步：下载 Docker Desktop

通过官方地址下载：

<Link url="https://www.docker.com/products/docker-desktop/" title="Docker Desktop 官方下载页面"/>

选择 **Download for Windows**，运行安装程序。

<AsyncImageGroup query={["Docker Desktop Windows installer WSL 2 backend installation setup screenshot","Docker Desktop Settings General Use WSL 2 based engine Windows screenshot"]} aspectRatio="5:3" layout="carousel"/>

安装时：

1. 选择 WSL 2 backend（不要选择 Docker VMM 或 Hyper-V backend）。
2. 完成安装，按提示重启 Windows。
3. 从 Windows 开始菜单启动 Docker Desktop。
4. 等待 Docker Engine 显示运行状态。

不同版本 Docker Desktop 的安装选项可能略有差异。WSL2 是我们这里需要的后端。<Cite refs={["turn720183search0","turn720183search7"]}/>

## 第 3 步：启用 WSL2 引擎

打开 Docker Desktop：

**Settings → General**

找到：

`Use WSL 2 based engine`

如果该选项可见，请勾选，并点击 **Apply & Restart**。

某些新版 Docker Desktop 在只支持 WSL2 的配置下会默认启用，不再显示这个选项。

## 第 4 步：打开 Ubuntu 集成

打开：

**Settings → Resources → WSL Integration**

<AsyncImage query="Docker Desktop Settings Resources WSL Integration Ubuntu toggle screenshot" aspectRatio="16:9"/>

找到你正在使用的 Ubuntu 发行版，将其开关设置为开启状态。

例如：

```text
Enable integration with my default WSL distro   ON

Ubuntu-22.04                                    ON
```

点击 **Apply & Restart**。

这一步完成后，Windows 上的 Docker Desktop 就可以向 Ubuntu 提供 `docker` 命令。<Cite ref="turn720183search0"/>

## 第 5 步：验证 Docker

重新打开 Ubuntu 终端，执行：

```bash
docker --version
docker compose version
docker info
```

如果仍显示 `docker: command not found`，先在 Windows PowerShell 执行：

```powershell
wsl --shutdown
```

再打开 Ubuntu，重新检查。

最后运行一个实际容器：

```bash
docker run --rm hello-world
```

成功时应该看到：

```text
Hello from Docker!
```

这说明 Docker CLI、Docker Engine 和拉取镜像功能都已工作。

**注意：不要再在 Ubuntu 中额外执行 `sudo apt install docker.io`。** 对于我们采用的 Docker Desktop + WSL2 方案，没有必要安装第二套 Docker Engine，还可能产生冲突。

---

# 第二部分：把 SkillShift-Bench 从 D 盘迁移到 WSL

这部分推荐在 Docker 安装成功后操作，也可以现在先做。

## 1. 理解为什么要迁移

你现在的路径是：

```text
/mnt/d/projects/zhangshuyi/SkillShiftBench/skillshift-bench
```

`/mnt/d` 对应 Windows 的 `D:\` 磁盘。

你准备迁移到：

```text
/home/shuyi/projects/SkillShiftBench/skillshift-bench
```

<box border radius="xl" padding={3} gap={2}>
  <text weight="medium" size="sm">迁移前：Windows D 盘</text>
  <row align="center" gap={2}>
    <icon name="hard-drive" color="secondary" size="lg"/>
    <box flex="1" background="surface-secondary" radius="md" padding={3}>
      <text size="sm">`D:\projects\zhangshuyi\SkillShiftBench`</text>
      <caption>WSL 通过 /mnt/d 跨文件系统访问</caption>
    </box>
  </row>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <text weight="medium" size="sm">迁移后：Ubuntu Linux 文件系统</text>
  <row align="center" gap={2}>
    <icon name="folder-check" color="success" size="lg"/>
    <box flex="1" background="surface-secondary" radius="md" padding={3}>
      <text size="sm">`/home/shuyi/projects/SkillShiftBench`</text>
      <caption>Linux 本地文件系统，适合 Docker 和开发工具</caption>
    </box>
  </row>
</box>

Docker 官方明确建议，把需要绑定到 Linux 容器的代码和数据放在 Linux 文件系统中，以获得更好的文件 I/O 性能和文件变化事件支持。<Cite ref="turn720183search4"/>

## 2. 检查当前目录和目标空间

在 Ubuntu 终端执行：

```bash
echo "$HOME"
df -h ~
df -h /mnt/d
du -sh /mnt/d/projects/zhangshuyi/SkillShiftBench
```

你应该看到 HOME 类似：

```text
/home/shuyi
```

注意：即使源目录位于 D 盘，WSL 默认的 Linux 虚拟磁盘也可能位于 Windows C 盘。

所以 **迁移到 `/home/shuyi` 不代表实际数据还在 D 盘**。

如果你的 C 盘空间很小，在下载大型网站备份之前，需要考虑迁移整个 WSL 发行版的虚拟磁盘位置，或者调整 Docker Desktop 的磁盘镜像存储位置。

## 3. 创建 Linux 项目目录

在 Ubuntu 执行：

```bash
mkdir -p ~/projects/SkillShiftBench
```

检查：

```bash
ls -ld ~/projects/SkillShiftBench
```

预期创建：

```text
/home/shuyi/projects/SkillShiftBench
```

## 4. 安全复制项目

推荐使用 `rsync`，而不是直接剪切或删除原文件。

先安装：

```bash
sudo apt update
sudo apt install -y rsync
```

然后复制整个 SkillShiftBench 父目录：

```bash
rsync -a --info=progress2 \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  /mnt/d/projects/zhangshuyi/SkillShiftBench/ \
  ~/projects/SkillShiftBench/
```

这里我特意排除了 Python 虚拟环境，因为迁移后原有 `.venv` 中的 Python 解释器路径、脚本 shebang 可能仍然指向旧目录。后续在新路径重新创建虚拟环境更稳妥。

如果你已经下载了很大的备份数据，这条命令也会复制它们，记得先检查空间。

该命令仅复制文件，不会删除 D 盘原文件。

## 5. 切换到新目录

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
```

确认：

```bash
pwd
ls -la
git status
```

预期路径：

```text
/home/shuyi/projects/SkillShiftBench/skillshift-bench
```

再检查两个文件系统：

```bash
df -T .
df -T /mnt/d
```

通常新目录会显示 Linux 文件系统 `ext4`，而 D 盘则显示 `9p`、`drvfs` 或其他 Windows 挂载类型。

可以再验证复制内容与源目录是否一致：

```bash
rsync -ani \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  /mnt/d/projects/zhangshuyi/SkillShiftBench/ \
  ~/projects/SkillShiftBench/
```

没有列出差异通常说明符合这些排除条件的文件已经复制完成。

如果出现路径或权限错误，先不要删除原目录。

## 6. 在新目录创建 Python 环境

你目前的终端提示符中有 `(base)`，说明 Conda base 环境已经激活。

为减少实验依赖冲突，建议给项目创建独立环境。

先检查官方 Python 版本约束：

```bash
grep -n 'requires-python' pyproject.toml
python3 --version
```

确认兼容后，可以退出 Conda base：

```bash
conda deactivate
```

然后：

```bash
sudo apt install -y python3-venv

python3 -m venv .venv
source .venv/bin/activate

python --version
which python
```

确认 `which python` 指向新的项目目录之后，再按照仓库要求安装依赖。

例如，如果该版本提供 `run` 可选依赖组：

```bash
python -m pip install -U pip
python -m pip install -e ".[run]"
```

这样就避免了原来 Conda、旧虚拟环境和 WSL 文件系统路径混用的问题。

# 第三部分：确保 GitLab 数据库不放在 Windows 挂载盘

这一步非常重要，因为 SkillShift-Bench 需要恢复网站数据库，并且可能反复重置实验环境。

Docker 中有两种常见的数据存储方式。

## 1. 推荐：Docker 命名卷

例如：

```yaml
services:
  database:
    image: postgres:16
    volumes:
      - gitlab_db:/var/lib/postgresql/data

volumes:
  gitlab_db:
```

这里的 `gitlab_db` 是 Docker 命名卷，不是 `/mnt/d` 目录。

Docker 会将它存储在 Docker Engine 管理的数据空间中。

<box gap={2}>
  <text weight="medium" size="sm">推荐的数据存储结构</text>
  <box border radius="lg" padding={3} gap={2} align="center">
    <box background="surface-secondary" padding={3} radius="md" width="100%" align="center" gap={1}>
      <icon name="monitor" size="lg"/>
      **Windows 11**
      <caption>Docker Desktop + WSL2 backend</caption>
    </box>
    <icon name="arrow-down" color="secondary"/>
    <grid columns={2} gap={2}>
      <grid-item>
        <box border radius="md" padding={3} gap={1} align="center">
          <icon name="folder-code" size="lg"/>
          <text weight="medium" size="sm">Ubuntu 项目文件</text>
          <caption textAlign="center">`/home/shuyi/projects/`</caption>
        </box>
      </grid-item>
      <grid-item>
        <box border radius="md" padding={3} gap={1} align="center">
          <icon name="database" size="lg"/>
          <text weight="medium" size="sm">Docker 数据卷</text>
          <caption textAlign="center">Docker Engine 管理</caption>
        </box>
      </grid-item>
    </grid>
    <caption>两者都避免将容器的高频读写数据直接放在 /mnt/d 下。</caption>
  </box>
</box>

## 2. 不推荐：数据库直接映射到 D 盘

例如下面这种配置：

```yaml
services:
  database:
    image: postgres:16
    volumes:
      - /mnt/d/docker-data/postgres:/var/lib/postgresql/data
```

对于数据库的高频读写，这样的配置通常不理想。

## 3. 另一种可行方案：Linux 目录绑定挂载

```yaml
services:
  database:
    image: postgres:16
    volumes:
      - /home/shuyi/docker-data/postgres:/var/lib/postgresql/data
```

这也能避免跨 Windows 文件系统读写，但需要保证目录权限正确。

**对于 SkillShift-Bench，建议先保留官方 Docker Compose 配置，不要直接替换它的数据库挂载方式。**

部署 GitLab 前，先检查：

```bash
cd ~/projects/SkillShiftBench/skillshift-envs

grep -R -nE 'volumes:|/mnt/[a-z]/|/var/lib/postgresql|/var/opt/gitlab' compose/
```

上述命令假定你已经下载了 `skillshift-envs`，并且该版本包含 `compose/` 目录。

还可以在确定具体 Compose 文件后运行：

```bash
docker compose -f <实际compose文件路径> config
```

观察最终解析出的 `volumes`，重点检查有没有引用 `/mnt/d/...`。

部署后，可以通过：

```bash
docker volume ls
docker volume inspect <实际卷名>
```

查看命名卷信息。

注意：Docker Desktop 的数据卷和镜像虽然不直接放在 `/mnt/d` 下，但它们最终仍由 Windows 主机上的虚拟磁盘文件承载。**不在 Windows 挂载盘上执行容器文件 I/O，与不占用 Windows 磁盘空间，是两件不同的事情。**

# 第四部分：是否需要把 Docker 和 WSL 都安装到 D 盘？

如果你的 C 盘空间比较紧张，这是值得提前考虑的。

Docker Desktop 的 WSL2 引擎默认将数据存储在 Windows 用户目录下，可以在：

**Docker Desktop → Settings → Resources → Advanced**

找到磁盘镜像位置设置，并按你的实际存储规划迁移到 D 盘。<Cite ref="turn720183search6"/>

这不会把容器数据库变成 `/mnt/d` 绑定挂载，因为数据仍然存放在 Linux 虚拟磁盘内部。

WSL Ubuntu 自己的虚拟磁盘则是另一回事。若要把整个 Ubuntu 发行版迁移到 D 盘，需要使用 WSL 的发行版迁移机制。建议先不做这一步，除非检查磁盘空间后确实有必要。

# 第五部分：迁移后如何在 Windows VS Code 打开项目？

你不需要再通过 `D:\projects` 打开它。

在 Ubuntu 终端执行：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
code .
```

安装 VS Code 的 WSL 扩展后，这会从 Windows 启动 VS Code，但项目文件仍在 Ubuntu 中。

这是 Docker 官方推荐的 WSL 开发方式。<Cite ref="turn720183search2"/>

你也可以通过 Windows 文件资源管理器访问：

```bash
explorer.exe .
```

或者在地址栏输入：

```text
\\wsl.localhost\Ubuntu\home\shuyi\projects\SkillShiftBench
```

其中 `Ubuntu` 需要替换成你的实际 WSL 发行版名称。

---

# 第六部分：完成后按这个清单检查

{@body const checks = ["Docker Desktop 已安装并正常启动","WSL Integration 已开启 Ubuntu","docker run --rm hello-world 成功","项目已复制到 /home/shuyi/projects/SkillShiftBench","新目录内的 Git 仓库状态正常","Python 虚拟环境在新路径重新创建","原 D 盘目录仍作为备份保留"]}
{@body const [done,setDone] = DIL.useState([])}
<box border radius="xl" padding={3} gap={2}>
  <row align="center" justify="between">
    **安装与迁移检查**
    <text color="secondary" size="xs" tabularNums>{done.length}/{checks.length} 完成</text>
  </row>
  <box background="surface-tertiary" height="6px" radius="full" clip>
    <box background="rgba(22,163,74,0.8)" width={`${done.length/checks.length*100}%`} height="100%" radius="full"/>
  </box>
  {#each checks as item,i}
    <checkbox key={i} checked={done.includes(i)} onChange={v=>setDone(p=>v?[...p,i]:p.filter(x=>x!==i))} lineThrough={false}>{item}</checkbox>
  {/each}
</box>

## 接下来先做什么？

建议按照以下顺序进行：

1. **先安装 Docker Desktop，测试 `hello-world`。**
2. 检查 Ubuntu 所在磁盘的剩余空间。
3. 用 `rsync` 把项目复制到 `/home/shuyi/projects/SkillShiftBench`。
4. 在新路径重建 Python 环境。
5. 最后开始部署 SkillShift-Bench 的 GitLab Source 环境。

先完成前两项之后，把下面命令的输出发给我：

```bash
docker --version
docker compose version
docker run --rm hello-world
echo "$HOME"
df -h ~ /mnt/d
```

我会根据结果继续指导你完成项目迁移，并检查是否需要调整 Docker Desktop 的存储位置，避免后面下载 GitLab 和 Magento 数据时遇到磁盘空间不足的问题。

## 用户

6. 在新目录创建 Python 环境中说的创建独立环境，是指该环境位于~/projects/SkillShiftBench/skillshift-bench$中吗？按照你的命令创建的环境的名称是什么

## ChatGPT

是的。按照我之前给你的命令，**Python 独立虚拟环境会创建在 `~/projects/SkillShiftBench/skillshift-bench/` 项目根目录下，环境名称为 `.venv`。**

### 1. 环境的位置和名称

假设你当前位于：

```bash
~/projects/SkillShiftBench/skillshift-bench$
```

执行：

```bash
python3 -m venv .venv
```

会创建：

```text
/home/shuyi/projects/SkillShiftBench/
└── skillshift-bench/
    ├── .venv/            # Python 虚拟环境
    │   ├── bin/
    │   ├── lib/
    │   └── pyvenv.cfg
    ├── data/
    ├── docs/
    ├── src/
    ├── pyproject.toml
    └── README.md
```

其中：

- **环境名称：** `.venv`
- **环境路径：** `/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv`
- **环境类型：** Python `venv`，不是 Conda 环境。

### 2. 创建并激活环境

在 Ubuntu 终端执行：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate
```

激活成功后，终端通常会变成：

```text
(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$
```

### 3. 如何确认环境已经激活？

执行：

```bash
which python
```

应输出：

```text
/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/bin/python
```

也可以执行：

```bash
echo $VIRTUAL_ENV
```

应输出：

```text
/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv
```

### 4. 与 Conda 环境有什么区别？

你之前的终端显示 `(base)`，说明你安装了 Conda。

| 对比项 | Python venv | Conda |
|---|---|---|
| 环境名称 | `.venv` | 可以自定义，例如 `skillshift` |
| 默认存储位置 | 项目根目录下 | Conda 的 `envs` 目录 |
| 激活命令 | `source .venv/bin/activate` | `conda activate skillshift` |
| Python 版本管理 | 依赖已有 Python | 可以安装指定 Python 版本 |
| 适合 SkillShift-Bench | 是 | 也可以 |

**我的建议：当前使用 `.venv` 即可。** 它与项目放在一起，方便 VS Code 自动识别，也能隔离项目依赖。

不过，在执行 `python3 -m venv .venv` 之前，最好先检查：

```bash
python3 --version
grep -n 'requires-python' pyproject.toml
```

确保系统 Python 版本符合 SkillShift-Bench 要求，再创建环境。

另外，如果你更喜欢环境名称叫 `skillshift`，也可以执行：

```bash
python3 -m venv skillshift
source skillshift/bin/activate
```

这样环境就会创建在项目根目录下的 `skillshift/` 文件夹中。

**建议继续使用 `.venv`，不要同时创建 `.venv` 和 `skillshift` 两套环境。**

## 用户

创建环境时出现：
(base) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$ python3 --version
Python 3.13.5
(base) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$ conda deactivate
shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$ sudo apt install -y python3-venv
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
The following additional packages will be installed:
  libpython3.12-minimal libpython3.12-stdlib libpython3.12t64
  python3-pip-whl python3-setuptools-whl python3.12 python3.12-minimal
  python3.12-venv
Suggested packages:
  python3.12-doc binfmt-support
The following NEW packages will be installed:
  python3-pip-whl python3-setuptools-whl python3-venv python3.12-venv
The following packages will be upgraded:
  libpython3.12-minimal libpython3.12-stdlib libpython3.12t64 python3.12
  python3.12-minimal
5 upgraded, 4 newly installed, 0 to remove and 211 not upgraded.
Need to get 10.7 MB of archives.
After this operation, 2797 kB of additional disk space will be used.
Get:1 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 libpython3.12t64 amd64 3.12.3-1ubuntu0.17 [2348 kB]
Get:2 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 python3.12 amd64 3.12.3-1ubuntu0.17 [651 kB]
Get:3 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 libpython3.12-stdlib amd64 3.12.3-1ubuntu0.17 [2071 kB]
Get:4 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 python3.12-minimal amd64 3.12.3-1ubuntu0.17 [2335 kB]
Get:5 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 libpython3.12-minimal amd64 3.12.3-1ubuntu0.17 [839 kB]
Get:6 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 python3-pip-whl all 24.0+dfsg-1ubuntu1.3 [1707 kB]
Get:7 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 python3-setuptools-whl all 68.1.2-2ubuntu1.2 [716 kB]
Get:8 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 python3.12-venv amd64 3.12.3-1ubuntu0.17 [5684 B]
Get:9 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 python3-venv amd64 3.12.3-0ubuntu2.1 [1032 B]
Fetched 10.7 MB in 4s (2733 kB/s)
(Reading database ... 57970 files and directories currently installed.)
Preparing to unpack .../0-libpython3.12t64_3.12.3-1ubuntu0.17_amd64.deb ...
Unpacking libpython3.12t64:amd64 (3.12.3-1ubuntu0.17) over (3.12.3-1ubuntu0.13) ...
Preparing to unpack .../1-python3.12_3.12.3-1ubuntu0.17_amd64.deb ...
Unpacking python3.12 (3.12.3-1ubuntu0.17) over (3.12.3-1ubuntu0.13) ...
Preparing to unpack .../2-libpython3.12-stdlib_3.12.3-1ubuntu0.17_amd64.deb ...
Unpacking libpython3.12-stdlib:amd64 (3.12.3-1ubuntu0.17) over (3.12.3-1ubuntu0.13) ...
Preparing to unpack .../3-python3.12-minimal_3.12.3-1ubuntu0.17_amd64.deb ...
Unpacking python3.12-minimal (3.12.3-1ubuntu0.17) over (3.12.3-1ubuntu0.13) ...
Preparing to unpack .../4-libpython3.12-minimal_3.12.3-1ubuntu0.17_amd64.deb ...
Unpacking libpython3.12-minimal:amd64 (3.12.3-1ubuntu0.17) over (3.12.3-1ubuntu0.13) ...
Selecting previously unselected package python3-pip-whl.
Preparing to unpack .../5-python3-pip-whl_24.0+dfsg-1ubuntu1.3_all.deb ...
Unpacking python3-pip-whl (24.0+dfsg-1ubuntu1.3) ...
Selecting previously unselected package python3-setuptools-whl.
Preparing to unpack .../6-python3-setuptools-whl_68.1.2-2ubuntu1.2_all.deb ...
Unpacking python3-setuptools-whl (68.1.2-2ubuntu1.2) ...
Selecting previously unselected package python3.12-venv.
Preparing to unpack .../7-python3.12-venv_3.12.3-1ubuntu0.17_amd64.deb ...
Unpacking python3.12-venv (3.12.3-1ubuntu0.17) ...
Selecting previously unselected package python3-venv.
Preparing to unpack .../8-python3-venv_3.12.3-0ubuntu2.1_amd64.deb ...
Unpacking python3-venv (3.12.3-0ubuntu2.1) ...
Setting up python3-setuptools-whl (68.1.2-2ubuntu1.2) ...
Setting up python3-pip-whl (24.0+dfsg-1ubuntu1.3) ...
Setting up libpython3.12-minimal:amd64 (3.12.3-1ubuntu0.17) ...
Setting up python3.12-minimal (3.12.3-1ubuntu0.17) ...
Setting up libpython3.12-stdlib:amd64 (3.12.3-1ubuntu0.17) ...
Setting up python3.12 (3.12.3-1ubuntu0.17) ...
Setting up libpython3.12t64:amd64 (3.12.3-1ubuntu0.17) ...
Setting up python3.12-venv (3.12.3-1ubuntu0.17) ...
Setting up python3-venv (3.12.3-0ubuntu2.1) ...
Processing triggers for systemd (255.4-1ubuntu8.16) ...
Job for systemd-binfmt.service failed because the control process exited with error code.
See "systemctl status systemd-binfmt.service" and "journalctl -xeu systemd-binfmt.service" for details.
Processing triggers for man-db (2.12.0-4build2) ...
Processing triggers for libc-bin (2.39-0ubuntu8.7) ...
/sbin/ldconfig.real: /usr/lib/milvus/libbson-1.0.so.0 is not a symbolic link

/sbin/ldconfig.real: /usr/lib/milvus/libmongoc-1.0.so.0 is not a symbolic link

/sbin/ldconfig.real: /usr/lib/milvus/libaio.so.1 is not a symbolic link

/sbin/ldconfig.real: /usr/lib/milvus/libmongocxx.so._noabi is not a symbolic link

/sbin/ldconfig.real: /usr/lib/milvus/libbsoncxx.so._noabi is not a symbolic link

## 深度思考

Searched 7 websites

## ChatGPT

从你提供的终端日志来看，**`python3-venv` 基本已经安装成功，可以继续创建 SkillShift-Bench 的 Python 虚拟环境。**

不过，有两个问题需要注意：

1. 你最初的 `python3 --version` 是 **Python 3.13.5**，但 Ubuntu 24.04（Noble）通过 `apt` 安装的是 **Python 3.12** 的 `venv` 组件。
2. 安装最后出现了 `systemd-binfmt.service` 启动失败，以及几个 Milvus 动态库警告。

这些信息并不意味着 `venv` 安装失败。我们先验证 Python 解释器路径，再决定用哪个版本创建环境。

## 一、为什么 Python 3.13.5 和 3.12 同时存在？

你的终端最初显示：

```text
(base) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$
```

说明你当时激活了 Conda 的 `base` 环境。

因此，最初执行：

```bash
python3 --version
```

得到的 Python 3.13.5 很可能来自 Conda，而非 Ubuntu 系统自带的 Python。

你执行：

```bash
conda deactivate
```

之后，系统 Python 很可能恢复为 Ubuntu 24.04 默认的 Python 3.12。

这两个 Python 可以同时存在，**不会天然产生冲突**。

## 二、现在先执行这四条命令

保持在当前项目目录：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench

which python3
python3 --version
/usr/bin/python3.12 --version
grep -n 'requires-python' pyproject.toml
```

主要确认两件事：

- `python3` 实际指向哪个解释器。
- SkillShift-Bench 的 `pyproject.toml` 要求哪个 Python 版本。

如果项目允许 Python 3.12，那么我建议优先用 Ubuntu 系统的 Python 3.12 创建虚拟环境，而不是使用 Conda 的 Python 3.13.5。

## 三、如何处理安装时的两个警告？

### 1. `systemd-binfmt.service failed`

你的日志：

```text
Job for systemd-binfmt.service failed because the control process exited with error code.
```

这属于 WSL 环境中可能出现的 systemd 服务问题，微软的 WSL 项目也有相关问题报告。它与 Python `venv` 不是同一个组件。<Cite ref="turn723309search1"/>

**目前不建议为了这个提示去修改 systemd 配置。**

如果后续系统功能出现异常，可以再检查：

```bash
systemctl status systemd-binfmt.service --no-pager
```

### 2. Milvus 的动态库警告

例如：

```text
/sbin/ldconfig.real: /usr/lib/milvus/libbson-1.0.so.0 is not a symbolic link
```

这是动态库文件链接形式的警告，通常不会影响 Python 虚拟环境的创建。

目前也不需要修改或删除这些 Milvus 库文件。

---

## 四、推荐使用 Python 3.12 创建环境

**前提：`pyproject.toml` 确认支持 Python 3.12。**

既然 Ubuntu 已经安装了 `python3.12-venv`，可以明确指定 Python 3.12，避免误用 Conda 中的 Python 3.13。

在项目根目录执行：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench

# 创建 Python 3.12 虚拟环境
/usr/bin/python3.12 -m venv .venv

# 激活环境
source .venv/bin/activate
```

终端应该变成：

```text
(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$
```

然后验证：

```bash
python --version
which python
python -m pip --version
```

预期：

```text
Python 3.12.x

/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/bin/python

pip ... from .../.venv/lib/python3.12/site-packages/pip
```

如果这些结果正常，说明独立环境创建成功。

之后才开始安装 SkillShift-Bench 项目依赖：

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[run]"
```

目前先不用运行后两条安装命令，优先确认项目的 Python 版本要求。

## 五、你现在需要做的事情

请在当前终端运行以下命令，把结果发给我：

```bash
which python3
python3 --version
/usr/bin/python3.12 --version
grep -n 'requires-python' pyproject.toml
```

我会根据输出确认是否应该使用 **Python 3.12**，然后继续指导你创建 `.venv`、安装依赖、配置 Playwright，直到 SkillShift-Bench 能正常运行。

## 用户

6.3 从官方备份部署 GitLab 12.0，当前步骤出现以下问题：
(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-envs$ ./setup.sh --site gitlab --condition src --dry-run
==> SkillShift-Bench environment setup
    site         gitlab
    condition    src
    version      v1
    environment  gitlab-v12
    source       ghcr.io/skillshift-bench/gitlab-v12:12.0.0
    URL          http://localhost:8080
    ports        8080 8443 2222
    timeout      900s
  !! dry run: nothing below is executed
==> pulling ghcr.io/skillshift-bench/gitlab-v12:12.0.0
    $ docker pull ghcr.io/skillshift-bench/gitlab-v12:12.0.0
==> starting gitlab-v12
    $ docker compose -f /home/shuyi/projects/SkillShiftBench/skillshift-envs/compose/gitlab-v12.yml -p skillshift-gitlab-v12 up -d
    $ /home/shuyi/projects/SkillShiftBench/skillshift-envs/scripts/healthcheck.sh --env gitlab-v12 --timeout 900

  OK gitlab-v12 is up
    Point the harness at it:

    export GITLAB_V1=http://localhost:8080

    Then, from your skillshift-bench checkout:

    skillshift env status
    skillshift run --agent reference --site gitlab --condition src

(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-envs$ docker ps -a
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-envs$ curl -I http://localhost:8080/users/sign_in
curl: (7) Failed to connect to localhost port 8080 after 0 ms: Couldn't connect to server

## ChatGPT

你当前的情况**不是 Docker 出错，也不是 GitLab 启动失败，而是因为你执行了 `--dry-run`（模拟运行）参数，GitLab 实际上还没有部署。**

这是正常现象。

## 一、为什么会出现这个问题？

你执行的是：

```bash
./setup.sh --site gitlab --condition src --dry-run
```

注意输出中的：

```text
!! dry run: nothing below is executed
```

这句话的意思是：

**仅展示接下来要执行的命令，不真正下载 Docker 镜像，也不启动容器。**

因此，虽然终端显示：

```text
OK gitlab-v12 is up
```

但这是模拟流程的输出，并不代表容器实际已经运行。

所以你之后执行：

```bash
docker ps -a
```

得到空列表：

```text
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

以及：

```bash
curl -I http://localhost:8080/users/sign_in
```

出现连接失败，都是符合预期的。

---

## 二、接下来应该如何操作？

### 第 1 步：确认 Docker 正常

先运行：

```bash
docker info
```

如果能正常输出 Docker Server 信息，说明 Docker Engine 已连接。

### 第 2 步：真正部署 GitLab 12.0

你的 `--dry-run` 显示脚本准备使用：

```text
ghcr.io/skillshift-bench/gitlab-v12:12.0.0
```

这是 GitLab 12.0.0 对应的容器镜像地址。

按照你之前的复现路线，可以先尝试官方备份恢复模式：

```bash
./setup.sh --site gitlab --condition src --from-hf
```

不过要注意：你的 dry-run 默认选择的是 GHCR 镜像来源，**`--from-hf` 会切换到另一条部署路径**，可能涉及备份下载及重建。它不一定是当前最简单的部署方式。

建议你先检查该脚本的帮助信息：

```bash
./setup.sh --help
```

如果官方 GHCR 镜像可访问，优先使用默认方式：

```bash
./setup.sh --site gitlab --condition src
```

如果提示 `manifest unknown`、`denied` 或镜像不可用，再考虑 `--from-hf`。

### 第 3 步：检查容器启动

部署命令执行后，运行：

```bash
docker ps -a
```

再检查：

```bash
docker compose -f compose/gitlab-v12.yml \
  -p skillshift-gitlab-v12 ps
```

注意：GitLab 初次启动涉及多个内部服务，容器处于 `Up` 并不一定代表 GitLab 已经准备好。

### 第 4 步：检查 HTTP 服务

```bash
curl -I http://localhost:8080/users/sign_in
```

如果返回 HTTP 响应，例如 `200` 或登录重定向响应，说明 Web 服务已经开始响应。

如果仍然出现：

```text
curl: (7) Failed to connect
```

就查看容器日志：

```bash
docker compose -f compose/gitlab-v12.yml \
  -p skillshift-gitlab-v12 logs --tail=100
```

这能帮助我们判断是镜像问题、端口问题，还是 GitLab 内部服务未成功启动。

---

## 三、你现在只需要做这一件事

在当前目录：

```text
~/projects/SkillShiftBench/skillshift-envs
```

执行：

```bash
./setup.sh --site gitlab --condition src
```

**这次不要加 `--dry-run`。**

如果成功，脚本会下载镜像、启动 Docker 容器并执行健康检查。

如果失败，把终端最后的报错发给我。我们根据实际错误处理，而不是提前修改 Docker 配置。

完成后，再进行下一阶段：设置 `GITLAB_V1`、确认 Benchmark 能连接 GitLab，然后运行第一个 GitLab 任务。

## 用户

现在我准备执行”七、第五步：配置模型 API“，但是执行前有一个问题想要确认：这里指定的模型是agent运行时的模型。评估是否使用模型；如果评估使用模型，是否和agent运行时的模型是一样的，且也是通过export my_model="你的模型名称"指定的？
此外，后续skillshift run会直接运行操作得到运行结果且返回评估结果？

## 深度思考

Searched 5 websites

## ChatGPT

你的理解基本正确。对于 SkillShift-Bench，需要明确区分 **Agent 运行模型** 和 **Benchmark 评估器（Evaluator）**。我查看了官方 Quickstart 和 Metrics 文档，可以回答你的两个问题。

## 一、Agent 模型与评估模型是什么关系？

**结论：`my_model` 用于配置官方 `reference` Agent 运行时调用的大模型；SkillShift-Bench 的任务成功判定由自动评分器完成，不需要另外配置一个 LLM-as-a-Judge 模型。**

可以这样理解整个执行流程：

<box border radius="xl" padding={3} gap={2}>
  <box background="surface-secondary" radius="md" padding={3} align="center" gap={1}>
    **Benchmark 任务**
    <text size="xs" color="secondary">例如：在 GitLab 中完成一个指定操作</text>
  </box>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <box border radius="md" padding={3} align="center" gap={1}>
    **Agent（使用你配置的大模型）**
    <text size="xs" color="secondary">`my_model` + `my_base_url` + `my_api_key`</text>
    <text size="xs" color="secondary">观察页面、推理、选择操作</text>
  </box>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <box border radius="md" padding={3} align="center" gap={1}>
    **Playwright / BrowserGym + GitLab**
    <text size="xs" color="secondary">执行点击、输入、导航等实际网站操作</text>
  </box>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <box border radius="md" padding={3} align="center" gap={1}>
    **自动评估器（Task Scorer）**
    <text size="xs" color="secondary">检查任务的成功条件，记录步骤和技能调用</text>
    <badge color="secondary">不需要单独的评估大模型</badge>
  </box>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <box background="surface-secondary" radius="md" padding={3} align="center" gap={1}>
    **任务运行结果**
    <text size="xs" color="secondary">Success、Steps、Skill Calls、Skill Failures</text>
  </box>
</box>

官方 Metrics 文档明确说明：

- `success` 来自任务自动评分器。
- `steps` 来自 Agent 执行循环。
- `skill_calls` 和 `skill_failures` 来自技能调用记录器 `SkillRecorder`。

因此，该 Benchmark 的标准任务评分不是另外调用 GPT 或其他大模型进行主观打分。<Cite ref="turn981760view1"/>

### 1.1 配置的三个环境变量分别是什么？

```bash
export my_api_key="你的API_KEY"
export my_base_url="https://api.example.com/v1"
export my_model="你的模型ID"
```

| 变量 | 用途 |
|---|---|
| `my_api_key` | Agent 调用模型服务时的认证密钥 |
| `my_base_url` | 模型 API 服务地址 |
| `my_model` | Agent 使用的模型 ID |

这三个变量是官方 Quickstart 中 `reference` Agent 的配置方式。<Cite ref="turn981760view0"/>

但要注意：如果以后改为自定义 Agent 或 MPCR，具体读取哪些环境变量，还需要看对应 Agent 实现，不能假设所有 Agent 都直接读取 `my_model`。

### 1.2 评估使用的模型是不是同一个？

对于标准任务成功率评估：

**没有单独的评估模型，所以不存在评估模型是否和 Agent 模型相同的问题。**

例如，假设你指定：

```bash
export my_model="gpt-5-mini-2025-08-07"
```

那么：

- Agent：使用 `gpt-5-mini-2025-08-07` 推理和执行操作。
- Benchmark：通过任务的自动评分逻辑判断操作是否成功。
- 不需要再配置 `judge_model`。
- 不会因为评估成功率而额外调用一个评分大模型。

但如果你自行在 Benchmark 外添加 LLM-as-a-Judge，这就属于你自己的扩展评估方案，需要另外配置模型，不是官方默认流程。

## 二、`skillshift run` 是否会直接运行并返回评估结果？

**是的。`skillshift run` 会实际运行 Agent、执行网站操作，并调用任务评分器得到评估记录。**

不过需要区分任务级评估和最终汇总指标。

### 2.1 运行单个任务

进入 Benchmark 目录：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
source .venv/bin/activate
```

配置 GitLab：

```bash
export GITLAB_V1=http://localhost:8080
```

配置模型 API 后运行：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.v1.0 \
  --out runs/first
```

这条命令会执行以下工作：

1. 加载指定任务 `skillshift.gitlab.v1.0`。
2. 初始化 `reference` Agent 和浏览器。
3. Agent 调用你指定的大模型进行推理。
4. Agent 对 GitLab 网页执行真实操作。
5. 任务结束时，自动评分器判断是否成功。
6. 将任务评估记录写入输出目录。

官方文档说明，`skillshift report` 使用任务级记录 `per_task.jsonl` 计算汇总结果。<Cite ref="turn981760view1"/>

任务记录中的主要字段类似：

```json
{
  "uid": "skillshift.gitlab.v1.0",
  "site": "gitlab",
  "condition": "src",
  "success": true,
  "steps": 8,
  "skill_calls": 0,
  "skill_failures": 0
}
```

这是**示意数据，不是真实运行结果**。

需要注意，`reference` 是无技能的 ReAct Agent，因此通常不会产生学习技能调用。

### 2.2 `run` 和 `report` 有什么区别？

| 命令 | 作用 | 是否调用 Agent 大模型 |
|---|---|---|
| `skillshift run` | 执行任务、自动评分、保存任务记录 | 是 |
| `skillshift report` | 从已保存记录计算 SR、AS、ASC、SFR | 否 |
| `skillshift validate` | 检查汇总结果格式及约束 | 否 |

也就是说，**一次 `run` 已经包含了任务评估，不需要另外运行一个模型评分步骤。**

但如果你想得到论文中使用的汇总指标，还需要执行 `report`。

例如：

```bash
skillshift report runs/first \
  --out submission/first/ \
  --name "Reference ReAct" \
  --model "$my_model"
```

其中 `--model "$my_model"` 用于在报告中记录模型名称，**不会重新执行模型推理，也不会切换评分模型**。

运行完成后，通常会生成 `results.json`、`run_receipt.json` 和 `per_task.jsonl` 等报告文件。官方说明 `per_task.jsonl` 保留本地，另两个文件用于提交结果。<Cite ref="turn981760view0"/>

只执行一个任务不满足完整 Benchmark 的任务覆盖要求，因此不要把这个单任务报告当作论文复现成绩。

## 三、对于你目前的复现目标，我建议这样做

你现在处于 GitLab Source 环境部署后的模型配置阶段。建议首先只运行一个任务，验证整条执行与评分链路。

<box border radius="lg" padding={3} gap={3}>
  <text weight="medium">下一步的操作顺序</text>
  <list marker="number" connector="solid" gap={2}>
    <list-item>**配置 Agent 模型 API**

      确保模型名称、接口地址、密钥正确。
    </list-item>
    <list-item>**验证 GitLab 环境**

      ```bash
      skillshift env status
      ```
    </list-item>
    <list-item>**运行一个任务**

      ```bash
      skillshift run --agent reference \
        --site gitlab --condition src \
        --tasks skillshift.gitlab.v1.0 \
        --out runs/first
      ```
    </list-item>
    <list-item>**检查任务结果**

      ```bash
      find runs/first -maxdepth 3 -type f
      ```

      找到实际生成的任务结果文件，检查 `success` 和 `steps`。
    </list-item>
    <list-item>**再扩展到 MPCR**

      在 reference Agent 跑通后，复现论文真正涉及的技能复用与适应方法。
    </list-item>
  </list>
</box>

最后强调一个对论文复现非常重要的区别：

**`reference` Agent 跑通，证明的是 Benchmark 执行与评分系统可用；并不意味着已经复现了论文提出的 MPCR 方法。** MPCR 还涉及冻结技能库、技能检索、执行和失败恢复等环节，需要按它自己的实现配置。

接下来，你可以告诉我**准备使用哪个模型和 API 服务商**（例如 GPT-5 mini、DeepSeek、Qwen 或其他 OpenAI 兼容接口）。我可以根据该模型给你准确的 `export` 配置，以及如何在运行正式任务前先验证模型 API 是否可用。

## 用户

在运行一个任务之前，我还有一些疑问：
如何理解论文表格中的website和environment两部分结果？
此外，对比的四种方法是skill learning methods, 所有的skill都是从src任务上学习得到的吗？那么表格中展示的src列的结果是否使用skill？如果使用，是通过再次运行一遍相同任务并加载skill实现的吗？其它五种设置使用的skill都是从src任务上学习得到的skill吗？
此外，你提供的skillshift run似乎没有指定skill learning method？

## ChatGPT

这几个问题关系到复现实验是否正确，尤其是“技能学习阶段”和“六种条件下的评测阶段”是否分开。我会对照论文的实验协议和仓库的运行接口确认，避免把 `reference` 的单任务测试误当成 AWM、ASI 等方法的复现。

## 深度思考

Searched 11 websites

## ChatGPT

你提出的这几个问题非常关键，因为它们涉及 SkillShift-Bench 的核心实验设计。尤其需要明确：**论文评估的不是单纯的 Web Agent，而是已经学习过技能的 Agent 在不同网站环境中的表现。**

我对照了论文第 3.1、3.3、5.1 节及附录 E.1，先给出四个核心结论：

1. **Website 和 Environment 是同一批实验结果的两种汇总维度**，不是两个独立的实验。
2. **四种方法都在 Source（Src）环境中学习技能**，但它们的学习机制不同，并不都是通过执行相同任务来生成技能。
3. **表格中的 `Src` 列也使用已学习的技能库**。`Src` 是原始环境中的评估结果，而不是技能学习阶段的成功率。
4. **你指出的问题是正确的**：我之前提供的 `skillshift run --agent reference` 只是验证 Benchmark 能否运行，没有指定 AWM、ASI、SkillWeaver 或 WALT，因此不能用于直接复现 Table 1。

下面把整个实验逻辑讲清楚。

## 一、如何理解 Website 和 Environment 两部分？

论文 Table 1 的列结构可以拆成：

<box border radius="lg" padding={3} gap={2}>
  <grid columns={2} gap={3}>
    <grid-item>
      <box background="surface-secondary" radius="md" padding={3} gap={2}>
        <text weight="medium">Website：按网站汇总</text>
        <text size="sm">GitLab</text>
        <text size="sm">Magento</text>
        <text size="sm">WordPress</text>
        <caption>每个网站综合六种环境条件</caption>
      </box>
    </grid-item>
    <grid-item>
      <box background="surface-secondary" radius="md" padding={3} gap={2}>
        <text weight="medium">Environment：按条件汇总</text>
        <text size="sm">Src / Src-Perc / Src-Exec</text>
        <text size="sm">Tgt / Tgt-Perc / Tgt-Exec</text>
        <caption>每个条件综合三个网站</caption>
      </box>
    </grid-item>
  </grid>
  <box align="center" gap={1}>
    <icon name="arrow-down-up" color="secondary"/>
    <text weight="medium" size="sm">来自同一组 Website × Environment 的任务执行记录</text>
  </box>
</box>

假设我们只研究 ASI 的 Success Rate（SR）。

### 1.1 Website 部分

截图中：

| 网站 | ASI 的 SR |
|---|---:|
| GitLab | 20.81% |
| Magento | 27.78% |
| WordPress | 60.27% |

其中 **GitLab 20.81%** 表示 ASI 在 GitLab 的六种条件下的总体任务成功率，而不是仅在 GitLab 原始版本上的成功率。

例如 GitLab 有 162 个任务族，每个任务族在六种条件下各评估一次，因此完整覆盖时共有：

\[
162\times6=972
\]

个 GitLab 任务实例。

20.81% 是对这些评估实例进行汇总得到的结果。

### 1.2 Environment 部分

同样看 ASI：

| 环境条件 | ASI SR | 含义 |
|---|---:|---|
| Src | 53.65% | 原始网站，未增加额外扰动 |
| Src-Perc | 48.80% | 原始网站，感知扰动 |
| Src-Exec | 24.43% | 原始网站，执行障碍 |
| Tgt | 41.84% | 网站升级后的环境 |
| Tgt-Perc | 33.19% | 升级环境 + 感知扰动 |
| Tgt-Exec | 15.79% | 升级环境 + 执行障碍 |

这里的 `Src` 53.65%，是综合 GitLab、Magento、WordPress 三个网站的 `Src` 任务实例所得的成功率。

可以看到：

- 从 Src 的 53.65% 降到 Tgt 的 41.84%，体现网站演化对技能迁移的影响。
- 从 Src 的 53.65% 降到 Src-Exec 的 24.43%，体现执行障碍带来的影响。
- Tgt-Exec 只有 15.79%，说明在网站演化并且存在执行障碍时，任务成功率进一步降低。

这些数字及六种条件的定义都直接来自论文 Table 1 和第 3.3 节。<Cite refs={["turn213864view0","turn213864view1"]}/>

### 1.3 用一张矩阵理解更直观

实际上，每种方法都需要评估一个 3 × 6 的矩阵：

| 网站 / 条件 | Src | Src-Perc | Src-Exec | Tgt | Tgt-Perc | Tgt-Exec |
|---|---|---|---|---|---|---|
| GitLab | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Magento | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WordPress | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

- **Website 列**：沿矩阵的行方向汇总六种条件。
- **Environment 列**：沿矩阵的列方向汇总三个网站。
- **O/A**：所有网站和环境条件的总体结果。

正式复现时应尽量保留每个任务实例的原始记录，再依据官方聚合规则计算这些指标，而不是直接对已经四舍五入的表格数字求平均。

**这里有一个重要的统计细节需要更正：** 我刚进一步核对了官方 `docs/metrics.md`。Table 1 使用的是 **Macro Average（宏平均）**，不是把所有网站的任务实例直接合并后求平均。

也就是说，GitLab 的 20.81% 先对每个条件中的 162 个任务求成功率，再对六个条件等权平均；Environment 的每个数值则是三个网站成功率的等权平均，而不是按 GitLab 162、Magento 114、WordPress 79 的任务数加权。O/A 是 18 个网站 × 条件单元的等权平均。<Cite ref="turn415946view2"/>

这意味着三个网站对最终指标的贡献相同，即使它们的任务数量不同。

## 二、四种方法的 Skill 都是从 Src 学到的吗？

**是的，论文第 5.1 节明确指出，AWM、ASI、SkillWeaver 和 WALT 都在 Src 环境中按照各自原生协议进行技能学习，再在对应的六种条件下评估。**

但是，“在 Src 环境学习”不等于“四种方法都先执行一遍全部 Src 任务”。

它们学习技能的方式有明显差异：

| 方法 | 学习的技能形式 | 技能如何产生 |
|---|---|---|
| AWM | 文本工作流 | 从成功的任务轨迹中抽取可复用步骤 |
| ASI | 可执行 Python 函数 | 从成功轨迹中归纳程序，再验证技能 |
| SkillWeaver | Playwright API 函数 | 自主探索网站、练习和调试技能 |
| WALT | 结构化工具 | 发现网站功能，演示、生成并验证工具 |

论文附录 E.1 特别指出，SkillWeaver 可以在不依赖 Benchmark 任务集合的情况下，通过主动探索生成学习机会；WALT 也采用网站功能探索机制。因此不能将四种方法的学习过程简单统一为“先跑一遍全部 Src 任务”。<Cite ref="turn213864view2"/>

### 2.1 整体实验流程

<box border radius="xl" padding={3} gap={2}>
  <box background="surface-secondary" padding={3} radius="md" align="center" gap={1}>
    **阶段 A：技能学习（Skill Acquisition）**
    <text size="xs" color="secondary">GitLab Src / Magento Src / WordPress Src</text>
    <text size="xs" color="secondary">AWM、ASI、SkillWeaver、WALT 分别学习</text>
  </box>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <grid columns={3} gap={2}>
    {#each ["GitLab","Magento","WordPress"] as site}
      <grid-item>
        <box border radius="md" padding={2} align="center" gap={1}>
          <icon name="library" size="lg"/>
          <text weight="medium" size="sm">{site}</text>
          <caption textAlign="center">学习得到的技能库</caption>
        </box>
      </grid-item>
    {/each}
  </grid>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <box background="surface-secondary" padding={3} radius="md" align="center" gap={1}>
    **阶段 B：固定技能库**
    <caption>保留学习好的技能，进入迁移评估</caption>
  </box>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <grid columns={3} gap={2}>
    {#each ["Src","Src-Perc","Src-Exec","Tgt","Tgt-Perc","Tgt-Exec"] as c}
      <grid-item>
        <box border radius="md" padding={2} align="center" gap={1}>
          <icon name="monitor" size="sm" color="secondary"/>
          <text weight="medium" size="xs">{c}</text>
        </box>
      </grid-item>
    {/each}
  </grid>
  <row justify="center">
    <icon name="arrow-down" color="secondary" size="lg"/>
  </row>
  <box background="surface-secondary" padding={3} radius="md" align="center" gap={1}>
    **阶段 C：自动评估及汇总**
    <text size="xs" color="secondary">SR / AS / ASC / SFR → Table 1</text>
  </box>
</box>

对于 ASI 与 MPCR 的比较，论文还明确要求固定同一个在 Src 学到的技能库。ASI 使用原来的技能选择器，MPCR 只改变测试时的候选动作选择和重排序，不重新学习技能。<Cite ref="turn273325view0"/>

## 三、Table 1 中的 Src 是重新评估吗？是否使用 Skill？

你的理解方向是对的。

**Src 列是带着已学技能在原始网站上进行评估，不是学习过程本身的成功率。**

以 ASI 为例，概念流程是：

<box border radius="lg" padding={3} gap={2}>
  <row align="center" gap={2}>
    <box background="surface-secondary" padding={3} radius="md" flex="1" gap={1}>
      **先在 GitLab Src 学习**
      <caption>执行学习协议，从成功经验中生成和验证 Python 技能</caption>
    </box>
    <icon name="arrow-right" color="secondary"/>
    <box background="surface-secondary" padding={3} radius="md" flex="1" gap={1}>
      **保存 GitLab 技能库**
      <caption>把通过验证的技能用于后续推理</caption>
    </box>
  </row>
  <row justify="center">
    <icon name="arrow-down" color="secondary"/>
  </row>
  <box border padding={3} radius="md" gap={1}>
    **再进行 Src 评估**

    在干净的 GitLab Src 状态下，Agent 可以调用保存的技能，也可以选择原始浏览器操作。Benchmark 独立记录任务是否完成。
  </box>
</box>

但是你问到的这一点需要更严谨地区分：

> 是否通过再次运行一遍相同任务并加载 Skill 实现？

论文明确规定了“学习阶段”和“评估阶段”，但我目前没有在公开的实验协议中找到足以确认 **每一个用于学习的具体任务，都在评估时原样重跑一次** 的完整任务划分说明。

因此，不能简单认定这是对同一批任务进行训练和测试。

需要区分三个概念：

- **同一网站环境**：学习和 Src 评估都使用原始版本的网站。
- **同一任务族**：六种评估条件使用相互对齐、保持任务目标的任务实例。
- **同一个学习样本**：学习阶段是否见过评估时的具体任务或轨迹，需要另外核对学习协议和任务清单。

论文能够确认前两点，但不能仅凭 Table 1 推出第三点。

另外，**加载了技能库不代表每个任务一定调用技能**。例如 ASI 在 Src 下的 ASC 是 0.18，说明平均每个任务只有 0.18 次显式技能调用。Agent 可以在技能可用的情况下，仍然选择普通浏览器操作。

因此，Src 的 SR 是“有技能可用的 Agent 在原始环境中的成功率”，而不是“全部任务都通过技能执行的成功率”。

## 四、其他五种条件使用的 Skill 也是从 Src 学到的吗？

**是的。论文中的核心迁移实验，就是将源环境学习到的技能迁移到其他环境条件中，而不是在每个新环境重新训练一套技能。**

以 ASI 的固定技能库实验为例：

| 评估条件 | 技能来源 | 是否重新学习技能 |
|---|---|---|
| Src | Src 学到的技能库 | 否 |
| Src-Perc | 同一个 Src 技能库 | 否 |
| Src-Exec | 同一个 Src 技能库 | 否 |
| Tgt | 同一个 Src 技能库 | 否 |
| Tgt-Perc | 同一个 Src 技能库 | 否 |
| Tgt-Exec | 同一个 Src 技能库 | 否 |

例如，在 GitLab 12 学到一个“创建 Issue”的技能，之后就可以检验它能否在 GitLab 16 中继续发挥作用。

在 Tgt 上，Agent 可能发现导航路径、按钮或页面结构发生了变化。它可以根据当前页面作出决策或恢复操作，但标准固定技能库协议不允许通过重新学习来更新已有技能库。

这才是论文关注的 **Skill Transfer under Environment Evolution（环境演化下的技能迁移）**。

论文还有一项额外实验：在 Magento 的 Tgt 环境重新学习 ASI 技能，再测试 Tgt-Perc 和 Tgt-Exec。那是专门研究重新学习是否优于源技能迁移的消融实验，不属于 Table 1 的标准条件。<Cite refs={["turn273325view1","turn983180search2"]}/>

## 五、为什么我之前给出的 `skillshift run` 没有指定 Skill Learning Method？

这一点你发现得完全正确。我之前的命令：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.v1.0 \
  --out runs/first
```

其中：

```bash
--agent reference
```

明确表示使用官方内置的 Reference Agent。

它是一个**没有已学习技能库的 ReAct Agent**，只使用基础浏览器动作。这条命令的作用是确认网站、模型、浏览器以及自动评分系统都能够正常工作。

它不能用于复现论文中的 ASI 53.65% 或 AWM 50.07% 等成绩。

更重要的是，我核对了官方 `docs/baselines.md`，发现一个对你的复现计划有直接影响的事实：

**官方并没有完整发布 Table 1 中四种方法的集成代码。**

| 组件 | 公开情况 |
|---|---|
| Benchmark 任务与评估器 | 已发布 |
| 网站部署环境 | 已发布 |
| Reference Agent | 已发布 |
| AWM 的论文实验集成 | 未发布 |
| ASI 的论文实验集成 | 未发布 |
| SkillWeaver 的论文实验集成 | 未发布 |
| WALT 的论文实验集成 | 未发布 |
| MPCR 实现 | 已发布 |
| ASI/MPCR 共享的冻结技能库 | 已发布 |

官方 Baselines 文档还指出，四种方法使用的上游仓库及精确 commit 尚未完整登记，因此不能保证只依靠当前仓库就能逐项重现 Table 1。<Cite ref="turn415946view0"/>

### 5.1 那么 `--agent` 应该怎么指定方法？

SkillShift-Bench 提供的是 Agent 接口。要使用特定方法，需要将这个方法包装成符合接口的 Agent。

例如：

```python
class MyAgent:
    def reset(self, task, recorder):
        ...

    def act(self, obs):
        ...
```

其中：

- `reset`：初始化当前任务，加载适当的技能库，并获取技能调用记录器。
- `act`：根据当前观察、任务目标和技能库产生下一步动作。

假设你将 ASI 集成实现为 `my_asi_agent.py`，并导出了 `ASIAgent` 类，才可以运行：

```bash
skillshift run \
  --agent my_asi_agent:ASIAgent \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.v1.0 \
  --out runs/asi-test
```

这里的 `my_asi_agent:ASIAgent` 只是接口格式示例，**不是官方仓库中已经存在、可以直接执行的类**。官方支持这种 `module:attribute` 加载形式。<Cite ref="turn415946view1"/>

### 5.2 目前官方发布的 MPCR 在哪里？

进入你的项目目录：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
```

执行：

```bash
find src/skillshift/agents/mpcr -maxdepth 3 -type f | sort
```

重点关注：

```text
src/skillshift/agents/mpcr/
├── actions/
├── workflows/
└── ... MPCR 实现文件
```

官方文档说明，`actions/` 包含 ASI 与 MPCR 实验使用的冻结技能函数，`workflows/` 包含工作流形式的参考材料。

你可以进一步执行：

```bash
grep -R -n -E "MPCR|mpcr|Factory|create_agent" \
  docs/ examples/ src/skillshift/agents/ | head -100

skillshift run --help
```

这样能够定位你的仓库版本提供的 MPCR 创建入口，再决定准确的 `--agent` 参数，而不是凭空假设某个命令存在。

---

## 六、重新规划你的复现路线

根据你的实际目标——复现论文 Table 1，我建议把实验过程拆为三个明确阶段。

| 阶段 | 需要完成什么 | 对应成果 |
|---|---|---|
| A. 基础复现 | GitLab + Reference Agent + 自动评估 | 证明基础系统能运行 |
| B. 技能迁移复现 | 使用已发布的固定技能库，运行 MPCR 与可用的对照实现 | 复现固定技能迁移和 MPCR 结果 |
| C. Table 1 复现 | 分别实现或集成 AWM、ASI、SkillWeaver、WALT 的技能学习与执行流程 | 尝试复现论文四种方法的完整结果 |

对于阶段 C，还需要认真处理学习数据与评估数据的关系、独立的技能库、模型版本、网站状态重置以及方法原生执行框架。仅安装 Benchmark 本身并不能自动完成四种方法的技能学习。

**我建议你现在先运行一个 `reference` 任务，验证基础环境；但如果你的主要研究目标是严格复现论文 Table 1，下一步最应该做的是梳理四种方法的 Skill Learning、Skill Storage、Skill Loading 和 Evaluation 实现，而不是直接全量运行 `skillshift run`。**

这两条路线可以并行推进，但要在实验记录中明确区分：**无技能 Agent 的连通性测试**与**已学习技能方法的迁移评估**，否则最后得到的结果无法与论文 Table 1 正确比较。

## 用户

我的目标是检查五种设置相对src的改变程度；为什么需要使用skill以及skill具体内容是怎样的。
不需要精确复现表格1的结果。
通过你的分析和ASC结果（skill使用率较低），SFR(skill错误率较为明显)，我发现skill对任务成功似乎并不是非常关键（论文似乎也没有给出无skill时的成功率）；更重要的是五种变化。
请重新规划接下来的复现路径（基础复现是必要的，技能迁移复现是需要考虑ASI这一种，因为MPCR使用的是ASI构建的skill 库）

## ChatGPT

我会把复现目标改成“研究五种环境变化相对于 Src 的影响”，而不是追求 Table 1 的数值。重点会放在：无技能基线、同任务配对比较、扰动机制检查，以及用 ASI 冻结技能库验证技能是否改变结论。我先核对官方代码目前支持哪些环节，避免把未发布的 ASI 学习流程当成现成功能。

## 深度思考

Searched 16 websites

## ChatGPT

# SkillShift-Bench 复现方案重新规划：以环境变化为核心

根据你现在明确的研究目标，我建议把复现方向从 **Skill Learning Benchmark 复现** 调整为 **Environment Shift Robustness Analysis（环境变化鲁棒性分析）**。

这会明显减少工作量，也更直接地回答你想研究的问题：

> 与原始环境 Src 相比，其他五种环境究竟发生了哪些变化？这些变化有多大？它们如何影响 Web Agent 的任务完成能力？Skill 在其中到底发挥了什么作用？

我建议采用：

**无 Skill Agent 作为主要实验对象，ASI 固定技能库作为辅助对照，MPCR 暂时不纳入必要实验。**

这一方案既能研究五种环境变化本身，又能检验 Skill 对鲁棒性究竟有没有贡献，而且不需要重新实现论文的全部四种方法。

## 一、首先修正两个关键认识

### 1. ASC 低不代表 Skill 不重要

你的观察有依据，但还不能直接得出 Skill 不关键的结论。

官方 Table 1 中，ASI 的 ASC 整体为 0.16，也就是说平均每个任务只有 0.16 次可执行 Skill 调用。

然而：

- 少量技能调用可能集中在最困难的任务。
- Skill 可能对某一类任务特别重要，而对其他任务没有作用。
- 任务没有调用 Skill，不代表技能库没有影响 Agent 的规划或动作选择。
- SFR 是对实际调用的 Skill 计算的失败比例，不能直接转化为任务失败比例。

官方指标文档也明确提醒：当技能调用次数很少时，SFR 可能由极少数调用决定，具有明显的统计不稳定性。<Cite ref="turn933773view1"/>

因此，需要通过 **有 Skill / 无 Skill 的受控对照实验** 判断 Skill 的实际贡献。

### 2. 环境变化可以在不使用 Skill 的条件下研究

这是你新的复现方案成立的关键。

尽管 SkillShift-Bench 最初是为了研究 Skill Transfer 而设计，但它的任务、网站环境、扰动机制以及任务评分器可以独立使用。

官方仓库还特别提供了不使用 Skill 的 `reference` Agent，能够在六种条件下运行，ASC 为 0、SFR 不适用。<Cite ref="turn933773view0"/>

这意味着你可以先研究：

\[
\text{Environment Shift} \rightarrow \text{Agent Performance Change}
\]

之后再加入 Skill，研究：

\[
\text{Skill Availability} \rightarrow \text{Robustness Change}
\]

这两个问题应该分开，而不是在第一次实验中混在一起。

---

## 二、重新定义你真正需要完成的实验

我建议把研究分成三个层次。

<box border radius="xl" padding={3} gap={3}>
  <row align="start" gap={3}>
    <box background="surface-secondary" radius="lg" padding={3}>
      <icon name="scan-search" size="lg"/>
    </box>
    <box flex="1" gap={1}>
      **实验 A：环境本身发生了什么变化？**

      不运行 Agent，直接分析版本差异、DOM/Locator 扰动、执行阻碍的注入方式和覆盖范围。
      <badge>最优先</badge>
    </box>
  </row>
  <divider color="subtle"/>
  <row align="start" gap={3}>
    <box background="surface-secondary" radius="lg" padding={3}>
      <icon name="bot" size="lg"/>
    </box>
    <box flex="1" gap={1}>
      **实验 B：变化对无 Skill Agent 的影响**

      使用同一个 Reference Agent，在相同任务族的六种条件下测试，计算相对 Src 的性能变化。
    </box>
  </row>
  <divider color="subtle"/>
  <row align="start" gap={3}>
    <box background="surface-secondary" radius="lg" padding={3}>
      <icon name="library" size="lg"/>
    </box>
    <box flex="1" gap={1}>
      **实验 C：Skill 能否抵御这些变化？**

      在同样的任务和模型下，使用 ASI 的冻结技能库，对比有 Skill 与无 Skill 的鲁棒性。
    </box>
  </row>
</box>

三个实验对应三个不同问题：

| 实验 | 核心问题 | 是否需要大模型 |
|---|---|---|
| A | 五种条件与 Src 在技术上相差多少？ | 不需要 |
| B | 五种变化让普通 Web Agent 退化多少？ | 需要 |
| C | 使用 ASI Skill 是否能改变退化幅度？ | 需要 |

建议按照 A → B → C 的顺序进行。

## 三、实验 A：直接研究五种环境变化本身

这是当前最值得优先投入精力的部分，而且可以在不调用 Agent 模型的情况下开展。

### 3.1 六种条件究竟改变了什么？

根据官方环境文档，这六种设置实际上是三个配置维度的组合：

| 条件 | 网站版本 | 感知扰动 | 执行扰动 |
|---|---|---|---|
| `src` | Source | 关闭 | 关闭 |
| `src-perc` | Source | 开启 | 关闭 |
| `src-exec` | Source | 关闭 | 开启 |
| `tgt` | Target | 关闭 | 关闭 |
| `tgt-perc` | Target | 开启 | 关闭 |
| `tgt-exec` | Target | 关闭 | 开启 |

**论文没有同时启用感知扰动和执行扰动的条件。** 因此不要把 `tgt-exec` 理解为“三种变化同时发生”。它是网站版本变化与执行扰动同时存在。<Cite ref="turn157027view1"/>

你真正想做的是以下五组比较：

<box border radius="xl" padding={3} gap={2}>
  <text weight="medium">以 Src 为固定参考</text>
  <grid columns={2} gap={2}>
    <grid-item>
      <box background="surface-secondary" radius="md" padding={3} align="center" gap={1}>
        <text color="secondary" weight="medium">Src</text>
        <caption>原始基准</caption>
      </box>
    </grid-item>
    <grid-item>
      <box border radius="md" padding={3} align="center" gap={1}>
        <text weight="medium">Src-Perc</text>
        <caption>只改变感知证据</caption>
      </box>
    </grid-item>
    <grid-item>
      <box border radius="md" padding={3} align="center" gap={1}>
        <text weight="medium">Src-Exec</text>
        <caption>只增加执行阻碍</caption>
      </box>
    </grid-item>
    <grid-item>
      <box border radius="md" padding={3} align="center" gap={1}>
        <text weight="medium">Tgt</text>
        <caption>只更换网站版本/主题</caption>
      </box>
    </grid-item>
    <grid-item>
      <box border radius="md" padding={3} align="center" gap={1}>
        <text weight="medium">Tgt-Perc</text>
        <caption>版本 + 感知变化</caption>
      </box>
    </grid-item>
    <grid-item>
      <box border radius="md" padding={3} align="center" gap={1}>
        <text weight="medium">Tgt-Exec</text>
        <caption>版本 + 执行阻碍</caption>
      </box>
    </grid-item>
  </grid>
</box>

不过在分析时，不能只计算相对于 Src 的差异，还应该加入两个非常有价值的配对比较：

\[
\text{Src-Perc}\leftrightarrow\text{Tgt-Perc}
\]

\[
\text{Src-Exec}\leftrightarrow\text{Tgt-Exec}
\]

这样才能将“网站版本变化”与“额外扰动”的影响更清楚地分开。

### 3.2 五种变化应该测量什么？

我建议记录两组指标。

| 变化 | 环境结构层面的指标 | Agent 执行层面的指标 |
|---|---|---|
| Src-Perc | Locator 属性变化数量、DOM 节点变化、目标元素可定位率 | 找不到目标、错误点击、重试 |
| Src-Exec | 阻挡元素数量、遮挡面积、操作不可用比例 | 点击失败、超时、恢复步骤 |
| Tgt | URL/路由变化、页面结构变化、目标元素位置变化 | 导航失败、找错功能入口 |
| Tgt-Perc | 版本变化 + 感知扰动的结构差异 | 目标查找错误、定位失败 |
| Tgt-Exec | 版本变化 + 执行障碍的结构差异 | 遮挡、超时、恢复失败 |

其中有一个非常重要的研究区分：

**环境变化程度，不等于任务性能下降程度。**

例如，一个网站升级可能导致大量无关 DOM 节点变化，但创建 Issue 的操作仍然十分相似。另一个版本可能只改变一个关键按钮的属性，却导致大量依赖旧 Locator 的操作失败。

因此，我建议将变化程度拆分为：

\[
D_{\mathrm{struct}}=\text{页面结构差异}
\]

\[
D_{\mathrm{critical}}=\text{任务关键元素差异}
\]

\[
D_{\mathrm{behavior}}=\text{操作可执行性差异}
\]

这三个指标不是论文已有的统一指标，而是为你的研究新增的分析维度。具体计算方法要基于扰动注入代码确定，不能直接把未经对齐的 DOM 文本编辑距离当作最终指标。

### 3.3 从哪里查看真实扰动实现？

进入你本地的仓库：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
source .venv/bin/activate
```

先查看任务和扰动相关源码：

```bash
find src/skillshift -maxdepth 3 -type f | sort

grep -R -nE \
  "perceptual|execution|src-perc|src-exec|tgt-perc|tgt-exec" \
  src/skillshift \
  | head -120
```

进一步定位注入机制：

```bash
grep -R -nE \
  "inject|perturb|overlay|modal|locator|occlud|intercept" \
  src/skillshift \
  | head -120
```

你需要确认：

- 感知扰动发生在浏览器真实 DOM 中，还是 Agent 接收到的观察信息中。
- 执行扰动是固定注入，还是仅在特定步骤触发。
- 扰动是否针对任务关键元素。
- 扰动是否需要由 Agent 显式调用 Skill 才会触发。

最后一点尤其重要：**如果某种执行扰动主要针对已学习的 Skill 操作，那么无 Skill Agent 可能没有经历同样的实际阻碍。** 这种情况下，无 Skill 实验仍然有价值，但不能将它解释为“所有 Agent 面对了完全相同的执行干扰”。

在这个阶段，建议先拿 GitLab 的一个任务进行六种条件下的页面对比，保存截图、Accessibility Tree、DOM 和可执行性检查结果。

---

## 四、实验 B：无 Skill Agent 的六条件对比

这是你研究中的主要量化实验。

### 4.1 为什么选择 Reference Agent？

它有三个优势：

1. 官方已经实现，不需要自己整合 ASI 等方法。
2. 使用基本浏览器操作，不依赖 Skill 学习阶段。
3. 能直接接入 Benchmark 的任务、扰动与自动评分器。

但它也有一个限制：Reference Agent 并不是论文 Table 1 使用的四种 Agent 之一，它的无 Skill 结果应作为**新的实验基线**，而非论文原有结果的复现。<Cite ref="turn933773view0"/>

### 4.2 实验设计

对每个任务族，使用相同的模型及 Agent 配置，在六种条件下分别运行。

例如：

| 任务族 | Src | Src-Perc | Src-Exec | Tgt | Tgt-Perc | Tgt-Exec |
|---|---|---|---|---|---|---|
| GitLab 任务 1 | 运行 | 运行 | 运行 | 运行 | 运行 | 运行 |
| GitLab 任务 2 | 运行 | 运行 | 运行 | 运行 | 运行 | 运行 |
| GitLab 任务 3 | 运行 | 运行 | 运行 | 运行 | 运行 | 运行 |

需要固定模型、提示词、采样参数、最大步骤数、任务初始状态和评估标准。对于模型随机性，可在资源允许时进行多次重复实验。

### 4.3 先运行 GitLab 的单任务验证

你已经在部署 GitLab 12.0，可以从这个环境开始。

首先运行：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
source .venv/bin/activate

export GITLAB_V1=http://localhost:8080

skillshift env status
```

确认模型 API 已配置，GitLab 正常后：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.v1.0 \
  --out runs/no_skill/gitlab-src
```

这里的任务 ID 是官方文档使用的示例。你的本地仓库如有不同任务 ID，应以实际任务清单为准。

之后在相同任务上执行：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src-perc \
  --tasks skillshift.gitlab.v1.0 \
  --out runs/no_skill/gitlab-src-perc
```

再执行 `src-exec`。这三组只需要 GitLab Source 环境。

下一步部署 GitLab Target（16.0.6），验证 `GITLAB_V2`，再执行 `tgt`、`tgt-perc` 和 `tgt-exec`。

在六个单任务实验成功后，再扩大到同一组 GitLab 任务，不建议直接开始 2,130 个实例的全量运行。

### 4.4 优先计算哪些指标？

你的主要研究目标是性能退化，因此我建议优先分析 SR 和 AS，再添加执行错误与恢复情况。

以 Src 为参考，成功率变化定义为：

\[
\Delta SR_c=SR_c-SR_{\mathrm{src}}
\]

例如，Src = 60%，Src-Exec = 35%，则：

\[
\Delta SR_{\mathrm{src-exec}}=-25\text{ 个百分点}
\]

平均步骤数变化：

\[
\Delta AS_c=AS_c-AS_{\mathrm{src}}
\]

此外，因为任务族是对齐的，我建议增加 **配对成功率变化分析**：

| Src 成功？ | 变化后成功？ | 解释 |
|---|---|---|
| 是 | 是 | 保持成功 |
| 是 | 否 | 成功转失败 |
| 否 | 是 | 失败转成功 |
| 否 | 否 | 保持失败 |

尤其需要关注：

\[
P(\text{Shift 失败}\mid\text{Src 成功})
\]

这能更直接地衡量环境变化造成了多少原本可以成功的任务失败。

如果只看宏平均 SR，就会丢失这部分任务级信息。配对分析还可以使用 bootstrap 置信区间；对于成功/失败配对，可以考虑 McNemar 检验。

## 五、实验 C：ASI Skill 是否真的有帮助？

我建议**保留 ASI，但不必重新运行 ASI 的技能学习过程**。

因为你关心的是环境变化和 Skill 的作用，而不是 Skill Learning 算法本身。

官方已经发布了 ASI 与 MPCR 共享的冻结技能库。根据 Baselines 文档，包含 24 个可执行 Python 技能：GitLab 8 个、Magento 12 个、WordPress 4 个。<Cite ref="turn933773view0"/>

### 5.1 为什么需要 Skill？

在原论文中，Skill 的作用是把复杂的浏览器操作封装成高层动作。

例如，普通 Agent 可能通过多个原始操作完成创建 Issue：

```text
进入项目
  ↓
进入 Issues
  ↓
点击 New issue
  ↓
填写标题
  ↓
填写描述
  ↓
提交
```

而 Skill Agent 可能通过一个高层动作执行这类流程：

```python
create_issue(project, title, description)
```

这是概念示例，不代表官方一定存在这个具体签名。

Skill 可能降低规划复杂度，但也可能固化原网站的 DOM、Locator、URL 和交互假设。网站变化后，这些假设不再成立，Skill 反而可能造成执行失败。

所以你可以研究两个问题：

- **Skill Benefit**：原始环境中，使用 Skill 是否比不用 Skill 更容易完成任务？
- **Skill Brittleness**：环境变化后，使用 Skill 的 Agent 是否比不用 Skill 的 Agent 更容易退化？

这是非常有意义的消融研究。

### 5.2 Skill 的具体内容怎么查看？

进入项目目录：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
```

查看现有技能库：

```bash
ls -lah src/skillshift/agents/mpcr/actions/
ls -lah src/skillshift/agents/mpcr/workflows/
```

列出技能函数及其签名：

```bash
python - <<'PY'
import ast
from pathlib import Path

root = Path("src/skillshift/agents/mpcr/actions")

for path in sorted(root.glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    print(f"\n=== {path.name} ===")
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            print(ast.unparse(node.args), "->", node.name)
PY
```

查看 GitLab 技能实现：

```bash
sed -n '1,240p' \
  src/skillshift/agents/mpcr/actions/gitlab.py
```

你应该重点检查这些方面：

| 检查维度 | 想知道什么 |
|---|---|
| 技能功能 | 这个 Skill 完成哪个任务或子任务？ |
| 输入参数 | 参数是否依赖特定网站结构？ |
| Locator | 是否硬编码按钮名称、CSS Selector、XPath？ |
| URL | 是否依赖 GitLab 12 的特定路由？ |
| 操作流程 | 是否包含固定操作顺序？ |
| 错误恢复 | 点击失败、超时后是否有处理逻辑？ |
| 泛化能力 | 是否能在 GitLab 16 继续执行？ |

**这部分可以先静态分析，不必立即接入 ASI Agent。**

如果技能函数中存在旧路由或硬编码 Locator，你就能进一步判断它们在五种环境变化下的失效风险。

### 5.3 ASI 对照实验应该怎么设计？

最理想的是三个实验组：

| 实验组 | Agent | 可用动作 | 目的 |
|---|---|---|---|
| B0 | Reference ReAct | 原始浏览器动作 | 官方无 Skill 基线 |
| B1 | ASI 风格 Agent，禁用 Skill | 原始浏览器动作 | 控制 Agent 实现差异 |
| B2 | 同一个 ASI 风格 Agent，启用 Skill | 原始动作 + 冻结 Skill | 检验 Skill 的净贡献 |

其中 **B1 与 B2 才是严格的 Skill 消融对照**。

因为如果直接拿 Reference Agent 和 ASI 比较，结果可能同时受到提示词、动作选择机制以及模型调用方式的影响，不能全部归因于 Skill。

需要特别说明：官方没有发布完整的 ASI Agent 集成，所以 B1/B2 需要基于公开的冻结技能库，自己实现或移植同一个执行器的有技能和无技能两种配置。

我建议先做最小版本：固定同一个 LLM Agent 的动作决策逻辑，使用一个开关控制是否将 24 个技能中对应网站的技能注册进动作空间。

为了避免实验信息泄漏，Agent 的 `reset` 接口虽然可以读取当前 condition，但如果目标是测量自然环境鲁棒性，应尽可能避免显式告知模型“这是 Src-Exec，可能会出现某种阻碍”，或者至少把是否提供条件标签作为单独控制变量。

### 5.4 怎样判断 Skill 是否改善了抗扰动能力？

不要只比较两个 Agent 在某个条件下的 SR，而应该比较二者的性能下降幅度。

定义：

\[
\Delta_c^{\text{NoSkill}}
=SR_c^{\text{NoSkill}}-SR_{\mathrm{src}}^{\text{NoSkill}}
\]

\[
\Delta_c^{\text{Skill}}
=SR_c^{\text{Skill}}-SR_{\mathrm{src}}^{\text{Skill}}
\]

进一步定义 Skill 的鲁棒性收益：

\[
R_c=\Delta_c^{\text{Skill}}-\Delta_c^{\text{NoSkill}}
\]

若 \(R_c>0\)，说明有 Skill 的 Agent 在该变化条件下相对 Src 的性能下降更小（或提升更大）。

若 \(R_c<0\)，说明 Skill Agent 的相对退化更严重。

要同时报告两个 Agent 的绝对 SR，因为相对退化更小，并不一定意味着最终成功率更高。

---

## 六、推荐的完整实验安排

我建议先以 GitLab 为主，完成从单任务到成体系比较的全过程，再扩展到 Magento 和 WordPress。

<box border radius="xl" padding={3} gap={3}>
  <text weight="medium">新的复现路线</text>
  <list marker="number" connector="solid" gap={3}>
    <list-item>
      **阶段 1：基础环境验证**

      完成 GitLab 12，配置模型 API，运行 Reference Agent 的单个 Src 任务，确认自动评分、运行日志和结果文件可用。
    </list-item>
    <list-item>
      **阶段 2：分析扰动源码**

      确认 `src-perc` 和 `src-exec` 的真实注入机制，记录扰动对象、触发条件、修改范围及是否依赖 Skill。
    </list-item>
    <list-item>
      **阶段 3：部署 GitLab 16**

      运行 GitLab Target，验证任务目标与初始状态的对齐关系。对同一个任务族检查六种条件。
    </list-item>
    <list-item>
      **阶段 4：无 Skill 六条件实验**

      先选择 5–10 个有代表性的任务族验证，再扩展到约 30–50 个任务族。保持同模型、同提示词和相同预算。
    </list-item>
    <list-item>
      **阶段 5：计算环境影响**

      计算各条件相对于 Src 的 SR、AS、任务成功转失败比例，并结合动作错误类型和环境结构变化进行解释。
    </list-item>
    <list-item>
      **阶段 6：ASI 技能库分析**

      阅读 8 个 GitLab 技能函数，统计硬编码路径、Locator、错误处理及版本相关依赖。
    </list-item>
    <list-item>
      **阶段 7：ASI 有/无 Skill 消融**

      在同一批 GitLab 任务上实现 B1/B2 对照，观察技能是否缓解或放大环境变化的影响。
    </list-item>
    <list-item>
      **阶段 8：扩展其他网站**

      将已验证的实验流程扩展至 Magento 与 WordPress，最终形成跨网站的变化分析。
    </list-item>
  </list>
</box>

### 最终希望得到的结果

你的核心结果表可以设计成：

| 条件 | 无 Skill SR | ΔSR vs Src | 有 Skill SR | ΔSR vs Src | Skill 鲁棒性收益 |
|---|---:|---:|---:|---:|---:|
| Src | 待测 | 0 | 待测 | 0 | — |
| Src-Perc | 待测 | 待测 | 待测 | 待测 | 待测 |
| Src-Exec | 待测 | 待测 | 待测 | 待测 | 待测 |
| Tgt | 待测 | 待测 | 待测 | 待测 | 待测 |
| Tgt-Perc | 待测 | 待测 | 待测 | 待测 | 待测 |
| Tgt-Exec | 待测 | 待测 | 待测 | 待测 | 待测 |

此外，建议增加一张“环境变化特征表”，把每个条件实际改变的关键 DOM、Locator、路由、阻挡元素和对应任务失败案例记录下来。

最终你不仅能回答“成功率下降多少”，还能尝试解释“为什么下降”。

## 七、MPCR 现在还需要吗？

**不作为必要实验。**

MPCR 使用 ASI 学习的冻结技能库，通过测试时的候选动作过滤和重排序改善执行可行性。其研究重点是执行器适应，而你的重点是变化程度本身。<Cite ref="turn867774search0"/>

保留 MPCR 作为后续可选扩展即可。如果你发现 Tgt-Exec 存在明显执行失败，并且希望进一步测试“执行器适应能否消除这部分退化”，再引入 MPCR 会更合适。

目前不需要重新执行 ASI 的 Skill Learning，也不用先复现 MPCR。

---

## 八、现在的下一步：先收集三项本地信息

为了让后续指导直接适用于你已经安装好的项目，建议先在终端执行：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
source .venv/bin/activate

# 1. 查看当前代码版本
git rev-parse --short HEAD

# 2. 查看运行接口
skillshift run --help

# 3. 查看扰动实现与 Skill 文件
find src/skillshift -maxdepth 3 -type f | sort
find src/skillshift/agents/mpcr/actions \
  -maxdepth 1 -type f | sort
```

再检查 GitLab：

```bash
export GITLAB_V1=http://localhost:8080
skillshift env status
```

把这几项结果发给我，我们下一步就可以**从真实源码入手，定位 Perceptual Shift 和 Execution Shift 到底修改了什么**，之后再运行第一个无 Skill 任务。

这样推进比直接全量跑 Benchmark 更符合你现在的研究目标，也能避免花费大量模型 API 成本之后，仍然不知道五种变化具体产生在什么地方。

## 用户

AB两组实验似乎都需要在实际运行后，才能更好的对比观察
src/skillshift/shifts/execution_shift.py
src/skillshift/shifts/perceptual_shift.py
我是否能够按照你提供的命令，六次执行任务后，分别得到实验A和实验B的结果，需要单独写评估代码吗？任务执行后的输出是否保留了足够的信息从A和B两方面评估

## ChatGPT

可以用同一任务的六次运行作为 A、B 两组实验的共同基础，但两者需要的信息不完全一样。我会先核对 `skillshift run` 默认保存哪些日志，以及两种 shift 在代码中何时注入，然后明确告诉你哪些指标现成可算、哪些需要补充记录。

## 深度思考

Searched 14 websites

## ChatGPT

# 可以六次运行，但必须保存完整轨迹

**结论：你的思路可行。使用同一个任务族，在六种环境条件下分别执行一次，可以同时为实验 A（环境变化分析）和实验 B（Agent 性能分析）收集数据。**

不过，经过核对 SkillShift-Bench 的实际运行代码，我发现一个非常重要的细节：

**`skillshift run` 默认只保存任务级评估结果，不保存完整的逐步执行轨迹。你需要增加 `--save-trajectories` 参数。**

这样，后续才有足够的信息分析 Agent 看到了什么、执行了什么、在哪里失败。

## 一、六次运行能得到哪些信息？

我直接核对了官方的三个实现文件：

- `src/skillshift/runner.py`
- `src/skillshift/eval/trajectory.py`
- `src/skillshift/cli.py`

实际支持的输出如下。<Cite refs={["turn681045view0","turn268725view2","turn268725view1"]}/>

| 你需要的数据 | 默认 `skillshift run` | 加 `--save-trajectories` |
|---|---|---|
| 任务是否成功 | <icon name="check" color="success" inline/> | <icon name="check" color="success" inline/> |
| 执行步骤数量 | <icon name="check" color="success" inline/> | <icon name="check" color="success" inline/> |
| Skill 调用次数 | <icon name="check" color="success" inline/> | <icon name="check" color="success" inline/> |
| 每一步执行的动作 | <icon name="x" color="danger" inline/> | <icon name="check" color="success" inline/> |
| 每一步访问的 URL | <icon name="x" color="danger" inline/> | <icon name="check" color="success" inline/> |
| Accessibility Tree | <icon name="x" color="danger" inline/> | <icon name="check" color="success" inline/> |
| HTML 观察内容 | <icon name="x" color="danger" inline/> | <icon name="check" color="success" inline/> |
| 动作错误信息 | 仅任务级错误 | <icon name="check" color="success" inline/> |
| 模型 Token 消耗 | <icon name="x" color="danger" inline/> | 可记录 |
| 每步截图 | <icon name="x" color="danger" inline/> | <icon name="x" color="danger" inline/> |
| 精确 DOM 变异事件 | <icon name="x" color="danger" inline/> | <icon name="x" color="danger" inline/> |
| 弹窗注入与关闭事件 | <icon name="x" color="danger" inline/> | 不保证完整 |

所以：

- **实验 B：** 原生输出基本足够计算任务成功率、平均步骤数、任务级退化与一部分执行错误。
- **实验 A：** 轨迹可以支持页面和行为差异的初步分析，但若要精确量化 DOM 变化、扰动覆盖率、弹窗触发次数，仍然需要额外记录。

我建议现在就打开完整轨迹，避免完成六次模型调用之后才发现缺少关键数据。

## 二、推荐的六次执行命令

你当前的项目路径为：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
source .venv/bin/activate
```

首先确认环境：

```bash
export GITLAB_V1=http://localhost:8080
export GITLAB_V2=http://localhost:8081

skillshift env status
```

GitLab 12 对应前三种条件，GitLab 16 对应后三种条件。因此，执行全部六种条件前，必须确保两个网站版本已经部署成功。

### 2.1 使用任务族 ID

官方 Quickstart 支持版本无关的任务族 ID：

```text
skillshift.gitlab.0
```

它会依据 `--condition` 自动选择对应的 v1 或 v2 任务版本。这样能避免把 v1 ID 错误地传给 Target 环境。<Cite ref="turn776137view3"/>

### 2.2 执行六个条件

下面的脚本按顺序运行六种条件，并分别保存结果：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench
source .venv/bin/activate

TASK="skillshift.gitlab.0"

for CONDITION in \
    src \
    src-perc \
    src-exec \
    tgt \
    tgt-perc \
    tgt-exec
do
    echo "================================"
    echo "Running $TASK / $CONDITION"
    echo "================================"

    skillshift run \
        --agent reference \
        --site gitlab \
        --condition "$CONDITION" \
        --tasks "$TASK" \
        --max-steps 10 \
        --workers 1 \
        --save-trajectories \
        --out "runs/shift_analysis/$CONDITION"
done
```

这里默认你已完成模型 API 配置，并且你的 `skillshift run --help` 显示支持 `--save-trajectories`。

如果 GitLab 16 尚未准备好，先只运行前三种条件：

```bash
for CONDITION in src src-perc src-exec
do
    skillshift run \
        --agent reference \
        --site gitlab \
        --condition "$CONDITION" \
        --tasks skillshift.gitlab.0 \
        --max-steps 10 \
        --save-trajectories \
        --out "runs/shift_analysis/$CONDITION"
done
```

**建议第一次先单独运行 Src 一个任务，检查日志文件正常生成，再启动整个循环。**

还要注意，同一任务的六次运行可能修改共享的网站数据库。正式做配对实验前，应确认每个任务开始时使用相同的基准数据状态，必要时执行官方重置流程，否则前一次任务创建的对象可能影响下一次任务。

## 三、运行后会生成哪些文件？

假设执行：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --save-trajectories \
  --out runs/shift_analysis/src
```

预期目录结构为：

```text
runs/
└── shift_analysis/
    └── src/
        ├── per_task.jsonl
        └── trajectories/
            └── skillshift.gitlab.v1.0.jsonl
```

### 3.1 `per_task.jsonl`：负责实验 B 的任务级指标

结构示意：

```json
{
  "uid": "skillshift.gitlab.v1.0",
  "site": "gitlab",
  "condition": "src",
  "success": true,
  "steps": 6,
  "skill_calls": 0,
  "skill_failures": 0,
  "error": null
}
```

数据为示例，不是实际结果。

这个文件已经能够支持：

- SR：任务成功率。
- AS：平均执行步骤数。
- 各条件相对于 Src 的 SR 变化。
- 同一任务族由成功转失败的比例。
- 任务级异常统计。

但如果每个条件只执行一个任务，SR 只能是 0% 或 100%，无法估计整体鲁棒性。

### 3.2 `trajectories/*.jsonl`：负责过程分析

官方 `StepTrace` 包含：

```json
{
  "uid": "skillshift.gitlab.v1.0",
  "step": 0,
  "url": "http://localhost:8080/...",
  "action": "...",
  "action_error": "",
  "reward": 0.0,
  "terminated": false,
  "truncated": false,
  "axtree": "...",
  "html": "...",
  "agent_usage": null,
  "judge_usage": []
}
```

同样是结构示例。

在这个文件中，每一行代表一个执行步骤。`axtree` 是 Agent 的页面可访问性观察，`html` 是页面观察文本，`action` 是执行的操作。

有一点需要注意：官方运行循环先从当前观察构造 `StepTrace`，然后执行动作，因此记录中的 `action_error` 来自该步之前的观察状态，不能未经处理就假设它是当前 `action` 的执行结果。<Cite refs={["turn681045view0","turn268725view2"]}/>

### 3.3 如何直接查看轨迹？

完成 Src 单任务后：

```bash
python - <<'PY'
import json
from pathlib import Path

p = Path(
    "runs/shift_analysis/src/trajectories/"
    "skillshift.gitlab.v1.0.jsonl"
)

for line in p.open(encoding="utf-8"):
    x = json.loads(line)
    print(f"\n===== STEP {x['step']} =====")
    print("URL:", x["url"])
    print("ACTION:", x["action"])
    print("ERROR:", x["action_error"])
    print("REWARD:", x["reward"])
    print("AXTREE:", x["axtree"][:1000])
PY
```

这样你可以逐步观察 Agent 的操作行为，而不必阅读一个很大的 JSONL 文件。

---

## 四、实验 A：现有轨迹是否足够分析环境变化？

**足够做初步分析，但不够支持完整的环境变化程度量化。**

我还核对了你提到的两个 Shift 文件，发现两种扰动机制非常具体。

### 4.1 Perceptual Shift 的实现

在 `perceptual_shift.py` 中，`DriftInjector` 可以生成三类变化：

- Visual：改变字体、按钮样式、背景或文字间距等。
- Locator：删除或改变 `data-testid`，添加干扰性的 CSS class。
- Structural：在一定条件下替换 `SPAN`、`B`、`I` 等标签。

源码还定义了 `low`、`medium`、`high` 三个强度档位，以及基于种子的伪随机扰动。<Cite ref="turn776137view1"/>

例如其定义的 `data-testid` 删除概率为：

| 强度 | 配置概率 |
|---|---:|
| Low | 10% |
| Medium | 40% |
| High | 80% |

但这些是注入器的配置概率，**不是某次任务实际发生的 DOM 变化比例**。还要检查当前任务配置具体启用了哪种扰动类型和强度。

因此，你可以分两个层次：

**第一层：静态变化配置。** 不需要运行 Agent，直接分析注入器参数、扰动范围和所使用的随机种子。

**第二层：实际变化效果。** 需要在任务执行时记录原始 DOM 和扰动后 DOM，计算实际变更的元素数量、关键 Locator 变化比例等。

仅靠 Agent 的执行轨迹无法准确还原原始 DOM 与扰动后 DOM 的一一对应关系，因为 Agent 在不同条件下可能走不同路径、访问不同页面。

### 4.2 Execution Shift 的实现

`execution_shift.py` 的 `InterferenceController` 提供了：

| 扰动模式 | 源码中的作用 |
|---|---|
| Addon 1 | 注入遮挡页面交互的弹窗 |
| Addon 2 | 注入 HTTP 500 错误 |
| Addon 3 | 注入约 10 秒网络延迟 |

对于弹窗，还支持：

- `once`：出现一次，关闭后不再出现。
- `multiple`：页面重新加载后可以再次出现。
- `random`：以指定概率、随机延迟出现。

这里有个重要发现：源码默认弹窗模式是 `once`，而 `random` 模式的默认注入概率是 0.5、最大延迟为 5 秒。**但要以运行任务时实际传入 `InterferenceController` 的参数为准，不能把这些默认值直接当作六条件实验的实际配置。** <Cite ref="turn749431view0"/>

为了评估 Execution Shift，我建议增加以下事件记录：

```json
{
  "event": "execution_shift_injected",
  "addon": "popup",
  "url": "http://localhost:8080/...",
  "timestamp": "...",
  "popup_mode": "once"
}
```

这也是示例结构，需要通过额外代码实现。

有了注入事件和动作轨迹后，你才能判断：

1. 扰动是否真的出现。
2. Agent 是否观察到了扰动。
3. Agent 是否尝试恢复。
4. 恢复成功还是失败。
5. 扰动使任务额外消耗了多少步骤。

**单凭 SR 和 AS，不能判断这些过程性问题。**

## 五、需要单独写评估代码吗？

我的建议是：**不要修改官方任务评分器，但需要编写一个独立的实验分析脚本。**

把评估分成三个层次即可：

| 层次 | 是否需要写代码 | 职责 |
|---|---|---|
| 官方任务评分 | 不需要 | 自动判断任务是否成功 |
| 实验 B 统计分析 | 需要少量代码 | 六条件 SR、AS、配对成功变化 |
| 实验 A 环境变化分析 | 需要额外采集和分析代码 | DOM 差异、扰动事件、错误恢复 |

### 5.1 实验 B 可以马上实现

先使用官方 `per_task.jsonl`，计算每个条件的 SR 和 AS。

下面是一段可以直接执行的分析代码，不需要安装 pandas：

```bash
python - <<'PY'
import json
from pathlib import Path

root = Path("runs/shift_analysis")
conditions = [
    "src", "src-perc", "src-exec",
    "tgt", "tgt-perc", "tgt-exec"
]

results = {}

for condition in conditions:
    file = root / condition / "per_task.jsonl"
    if not file.exists():
        print(f"{condition}: 尚无数据")
        continue

    rows = [
        json.loads(line)
        for line in file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        print(f"{condition}: 文件为空")
        continue

    sr = sum(bool(r["success"]) for r in rows) / len(rows)
    avg_steps = sum(r["steps"] for r in rows) / len(rows)
    results[condition] = (sr, avg_steps, len(rows))

src_sr = results.get("src", (None, None, None))[0]

print("\nCondition       N     SR       AS     ΔSR(pp)")
print("-" * 54)

for condition in conditions:
    if condition not in results:
        continue

    sr, avg_steps, n = results[condition]
    delta = (
        f"{(sr-src_sr)*100:+.2f}"
        if src_sr is not None else "N/A"
    )
    print(
        f"{condition:<15} {n:<5} "
        f"{sr*100:6.2f}%  {avg_steps:6.2f}  {delta:>8}"
    )
PY
```

这段程序适合初步验证；正式报告时还应校验任务族是否完全对齐、是否存在重复记录，并只比较相同任务族的结果。

### 5.2 实验 A 需要补充的采集机制

我建议先不要大规模改造代码，只增加一个最小的环境诊断采集器。

它需要保存：

- 每个任务初始页面的完整 DOM 和截图。
- 关键交互节点在扰动前后的属性。
- Perceptual Shift 实际修改的节点数量和类型。
- Execution Shift 的注入事件、触发时间和关闭事件。
- 页面导航、操作失败和恢复行为。

建议把这些诊断数据放在独立目录：

```text
runs/shift_analysis/
├── src/
│   ├── per_task.jsonl
│   └── trajectories/
├── src-perc/
├── src-exec/
├── tgt/
├── tgt-perc/
├── tgt-exec/
└── diagnostics/
    ├── dom_snapshots/
    ├── screenshots/
    ├── shift_events/
    └── comparisons/
```

当前官方 `--save-trajectories` 不会自动创建上述 `diagnostics/`，需要你后续添加采集逻辑。

而且，诊断代码应尽量采用只读观察和事件监听方式，避免修改网页内容、控制 Agent 动作或改变任务结果。

## 六、还有一个与模型 API 相关的重要更正

进一步阅读 `src/skillshift/eval/llm_judge.py` 后，需要修正我之前关于“评估完全不调用大模型”的说法。

**SkillShift-Bench 的一部分 WebArena 评分器确实使用 LLM Judge。**

具体来说：

- Agent 使用模型执行任务。
- 某些任务的语义匹配、答案匹配和 HTML 内容评估可能调用 LLM Judge。
- Judge 读取的也是 `my_api_key`、`my_base_url`、`my_model`。
- 评分可以在 `env.step()` 时触发，并非只在任务结束时调用。
- `--save-trajectories` 会将模型用量记录分别放在 `agent_usage` 与 `judge_usage` 中。<Cite refs={["turn749431view3","turn268725view2"]}/>

所以当前版本中，Agent 和部分评估器默认会使用同一套模型配置。

对于你的六条件实验，这意味着还需要保证 Judge 模型和评分规则一致，否则评分本身可能成为额外变量。

---

## 七、我建议你现在按以下顺序推进

<box border radius="lg" padding={3} gap={2}>
  <list marker="number" connector="solid" gap={2}>
    <list-item>**运行一个 Src 任务**

      加 `--save-trajectories`，确认真实输出结构与字段内容。
    </list-item>
    <list-item>**运行 Src-Perc 与 Src-Exec**

      使用同一个任务族 ID，保留执行轨迹。
    </list-item>
    <list-item>**确认扰动真正生效**

      检查 `DriftInjector` 和 `InterferenceController` 的调用入口及参数，而不只是看到 `--condition` 设置正确。
    </list-item>
    <list-item>**运行三个 Target 条件**

      在 GitLab 16 部署、任务状态重置和版本检查都通过之后执行。
    </list-item>
    <list-item>**先分析六次运行记录**

      确认能提取任务成功率、操作步骤、页面观察和错误信息。
    </list-item>
    <list-item>**再补充实验 A 的采集器**

      根据前面发现的数据缺口，添加扰动前后 DOM 快照和注入事件记录。
    </list-item>
  </list>
</box>

### 现在最优先的一条命令

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 10 \
  --save-trajectories \
  --out runs/shift_analysis/src
```

运行结束后检查：

```bash
find runs/shift_analysis/src -type f

cat runs/shift_analysis/src/per_task.jsonl

head -n 1 \
  runs/shift_analysis/src/trajectories/skillshift.gitlab.v1.0.jsonl
```

其中轨迹可能包含很长的 HTML、Accessibility Tree 和页面内容，不必把整份轨迹直接粘贴到聊天中。

**最终建议：六次运行可以作为两个实验的共同数据采集基础，但不要把六次 Agent 轨迹直接等同于五种环境变化的精确测量。** 实验 B 可以依靠现有评估输出开展；实验 A 则应在六次运行的基础上增加受控页面快照和扰动事件采集。

这样你后续才能把“环境实际上改变了多少”和“Agent 因这些改变损失了多少性能”建立可信的联系。

## 用户

(.venv) shuyi@DESKTOP-7HNQ7U2:\~/projects/SkillShiftBench/skillshift-bench$ export my_api_key="ark-1e557660-6997-4aa9-xxxx"\
(.venv) shuyi@DESKTOP-7HNQ7U2:\~/projects/SkillShiftBench/skillshift-bench$ export my_base_url="https\://ark.cn-beijing.volces.com/api/v3"\
(.venv) shuyi@DESKTOP-7HNQ7U2:\~/projects/SkillShiftBench/skillshift-bench$ export my_model="deepseek-v4-1-flash-economy-261017"\
(.venv) shuyi@DESKTOP-7HNQ7U2:\~/projects/SkillShiftBench/skillshift-bench$ python - <<'PY'\
import os\
\
for key in ["my_api_key", "my_base_url", "my_model"]:\
&#x20;   value = os.getenv(key)\
&#x20;   print(f"{key}: {'configured' if value else 'MISSING'}")\
PY\
my_api_key: configured\
my_base_url: configured\
my_model: configured\
(.venv) shuyi@DESKTOP-7HNQ7U2:\~/projects/SkillShiftBench/skillshift-bench$&#x20;

我准备执行：
```
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 10 \
  --save-trajectories \
  --out runs/shift_analysis/src
```

以上模型相关的环境配置是否正确

## 深度思考

Searched 3 websites

## ChatGPT

**是的，你的模型 API 配置在格式上是正确的。** 我核对了火山引擎方舟的官方文档，你填写的 API 地址和模型 ID 都有效。

不过，**环境变量显示 `configured` 只能证明已经设置，不能证明 API Key 有效、账户有调用权限或 SkillShift-Bench 能成功使用该模型。**

建议正式运行任务前，先做一次最小 API 测试。

## 一、检查你的三个配置项

| 环境变量 | 当前配置 | 检查结果 |
|---|---|---|
| `my_api_key` | `ark-...` | 格式看起来合理，尚未验证认证 |
| `my_base_url` | `https://ark.cn-beijing.volces.com/api/v3` | <icon name="check-circle" color="success" inline/> 正确 |
| `my_model` | `deepseek-v4-1-flash-economy-261017` | <icon name="check-circle" color="success" inline/> 官方支持 |

火山方舟官方模型列表明确包含 `deepseek-v4-1-flash-economy-261017`，并支持 Chat Completions API。因此，你不需要为了这个模型修改 Base URL。<Cite refs={["turn806042search0","turn743693search0"]}/>

## 二、先运行一次 API 连通性测试

在当前 `.venv` 环境中执行：

```bash
python - <<'PY'
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["my_api_key"],
    base_url=os.environ["my_base_url"],
    timeout=60,
)

response = client.chat.completions.create(
    model=os.environ["my_model"],
    messages=[
        {"role": "user", "content": "只回复 OK"}
    ],
    max_tokens=128,
)

print("Model:", response.model)
print("Content:", response.choices[0].message.content)
print("Finish reason:", response.choices[0].finish_reason)
print("Usage:", response.usage)
PY
```

这段代码会实际调用一次模型 API，可能产生少量费用。

如果正常返回模型响应，就说明：

- API Key 能够通过认证。
- 你的模型 ID 可以被调用。
- WSL 能够访问火山方舟。
- Python OpenAI SDK 能正常通信。

不一定严格回复 `OK`，只要返回有效的模型响应、没有 API 错误即可。

如果遇到 `ModuleNotFoundError: No module named 'openai'`，可以在虚拟环境中安装：

```bash
python -m pip install openai
```

注意，最小文本测试成功不代表 Agent 使用的所有参数和响应格式都兼容，但可以先排除大部分连接问题。

## 三、通过后，再运行 SkillShift-Bench

先检查 GitLab：

```bash
export GITLAB_V1=http://localhost:8080
skillshift env status
```

如果 GitLab 12 正常，再执行：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 10 \
  --workers 1 \
  --save-trajectories \
  --out runs/shift_analysis/src
```

这里的 `--max-steps 10` 是初次测试时设置的最大操作步数，并非论文原始实验预算。

有一点值得留意：你选择的 DeepSeek-V4.1-Flash Economy 是支持深度思考的模型。火山方舟对其输出 token 和思考模式有专门的参数规则。<Cite ref="turn806042search3"/> 如果后续运行出现空动作、输出截断或参数不兼容，我们需要检查 `reference` Agent 发送的实际模型参数，而不能仅凭 API 连通性成功就认定 Agent 兼容。

## 四、运行结束后检查结果

```bash
find runs/shift_analysis/src -type f
```

查看任务级结果：

```bash
cat runs/shift_analysis/src/per_task.jsonl
```

如果出现 `success: false`，不一定代表 API 配置错误。可能是 Agent 没完成任务、步数耗尽或网站交互失败，需要结合运行日志与轨迹判断。

另外，你展示的 API Key 已经做了部分遮挡，这是正确的。后续给我发送日志时，继续不要粘贴完整 API Key，也不要把密钥提交到 Git 仓库。如果完整密钥曾经公开泄露，应在火山方舟控制台将其轮换。

**建议现在先执行第二部分的最小 API 测试。** 如果能成功获得有效响应，你就可以开始第一个 GitLab Src 任务；如果报错，把错误内容（去除密钥）发给我，我们再定位具体问题。

## 用户

出现报错：
(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$ skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 10 \
  --workers 1 \
  --save-trajectories \
  --out runs/shift_analysis/src
running gitlab / src ...
2026-11-11 17:27:46,207 - Task skillshift.gitlab.v1.0 failed during execution
Traceback (most recent call last):
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/src/skillshift/runner.py", line 126, in run_task
    raw_obs, _ = env.reset()
                 ^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/wrappers/common.py", line 151, in reset
    return super().reset(seed=seed, options=options)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/core.py", line 348, in reset
    return self.env.reset(seed=seed, options=options)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/wrappers/common.py", line 431, in reset
    return super().reset(seed=seed, options=options)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/core.py", line 348, in reset
    return self.env.reset(seed=seed, options=options)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/wrappers/common.py", line 321, in reset
    self._previous_data = env_reset_passive_checker(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/utils/passive_env_checker.py", line 274, in env_reset_passive_checker
    result = env.reset(**kwargs)
             ^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/browsergym/core/env.py", line 191, in reset
    self.task = self.task_entrypoint(seed=seed, **self.task_kwargs)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/src/skillshift/tasks/task.py", line 199, in __init__
    self.webarena_instance = MyBenchmarkInstance()
                             ^^^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/src/skillshift/tasks/instance.py", line 32, in __init__
    assert env_var_name in os.environ, (
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Environment variable SHOPPING_ADMIN_V1 missing.
Please set SHOPPING_ADMIN_V1 to the URL of the v1 version of SHOPPING_ADMIN.
  skillshift.gitlab.v1.0           fail steps=0 skills=0

1 task record(s) written to runs/shift_analysis/src/per_task.jsonl
trajectories/ holds this run's per-step traces (actions, observations, token usage) for local debugging. Same rule as per_task.jsonl: do not commit it, do not attach it anywhere public. It is covered by the repository's .gitignore and is not part of the receipt.
Next: skillshift report runs/shift_analysis/src --out submission/ --name <method> --model <model>

## 深度思考

Searched 12 websites

## ChatGPT

这个报错已经明确指出了问题所在：**不是模型 API 出错，也不是 Agent 推理失败，而是 SkillShift-Bench 在初始化 BrowserGym 任务时，发现缺少网站环境变量 `SHOPPING_ADMIN_V1`。**

你的任务实际上还没有开始执行：

```text
AssertionError: Environment variable SHOPPING_ADMIN_V1 missing.
Please set SHOPPING_ADMIN_V1 to the URL of the v1 version of SHOPPING_ADMIN.

skillshift.gitlab.v1.0  fail steps=0 skills=0
```

这说明：

1. `skillshift run` 已经正常启动。
2. Benchmark 已经识别 GitLab 任务 `skillshift.gitlab.v1.0`。
3. 程序在 `env.reset()` 阶段失败，尚未进入 Agent 的模型推理和网站操作。
4. `fail steps=0` 是环境初始化失败，并不代表 Agent 没有完成任务。

## 一、为什么运行 GitLab 任务却需要 SHOPPING_ADMIN？

这是由于 SkillShift-Bench 复用了 WebArena 的网站环境配置。

从你的调用栈可以看到：

```text
skillshift/tasks/task.py
    ↓
MyBenchmarkInstance()
    ↓
skillshift/tasks/instance.py
    ↓
检查环境变量
    ↓
SHOPPING_ADMIN_V1 missing
```

因此，即使你只准备运行 GitLab，`MyBenchmarkInstance` 也可能在初始化阶段要求其他网站的 URL 环境变量。

**这里的 `SHOPPING_ADMIN` 通常指 Magento 的管理后台，并不表示你的 GitLab 任务被错误地当成了 Magento 任务。**

不过，我们需要根据你当前的 `instance.py` 确认它到底检查了哪些变量，避免出现设置一个变量之后又缺少下一个的问题。

## 二、已确认：源码要求六个网站环境变量全部存在

我核对了官方仓库的 `src/skillshift/tasks/instance.py`，问题已经定位。

代码中定义：

```python
AVAILABLE_VERSIONS = ["v1", "v2"]
SITE_NAMES = ("GITLAB", "SHOPPING_ADMIN", "WORDPRESS")
```

随后通过双层循环检查所有网站的 v1、v2 URL。也就是说，**即使只运行 GitLab v1，也要求六个变量都存在**。<Cite ref="turn642401view0"/>

六个变量分别是：

| 环境变量 | 对应网站 | 官方默认地址 |
|---|---|---|
| `GITLAB_V1` | GitLab 12 | `http://localhost:8080` |
| `GITLAB_V2` | GitLab 16 | `http://localhost:8081` |
| `SHOPPING_ADMIN_V1` | Magento 1.9 | `http://dockerized-magento.local/admin` |
| `SHOPPING_ADMIN_V2` | Magento 2.4 | `http://localhost:7780/admin` |
| `WORDPRESS_V1` | WordPress Source | `http://localhost:8000` |
| `WORDPRESS_V2` | WordPress Target | `http://localhost:8000` |

这些地址来自官方环境部署说明。WordPress v1、v2 共用一个实例，通过切换主题区分版本。<Cite ref="turn815881view0"/>

## 三、解决方法：一次性设置六个变量

你现在位于：

```text
~/projects/SkillShiftBench/skillshift-bench
```

直接执行：

```bash
# GitLab
export GITLAB_V1="http://localhost:8080"
export GITLAB_V2="http://localhost:8081"

# Magento
export SHOPPING_ADMIN_V1="http://dockerized-magento.local/admin"
export SHOPPING_ADMIN_V2="http://localhost:7780/admin"

# WordPress
export WORDPRESS_V1="http://localhost:8000"
export WORDPRESS_V2="http://localhost:8000"
```

**注意：现在不需要安装 Magento 和 WordPress。**

对于这次 GitLab v1 任务，其他四个 URL 主要用于通过初始化检查。只要程序没有实际访问这些网站，就不要求它们已经启动。

不过，这些 URL 是配置值，并不代表对应网站已经部署成功。

### 3.1 验证环境变量

执行：

```bash
python - <<'PY'
import os

sites = ["GITLAB", "SHOPPING_ADMIN", "WORDPRESS"]

for site in sites:
    for version in ["V1", "V2"]:
        key = f"{site}_{version}"
        print(f"{key}: {os.getenv(key, 'MISSING')}")
PY
```

预期六个变量都能显示对应 URL。

### 3.2 确认 GitLab 12 真的能够访问

执行：

```bash
curl -I http://localhost:8080/users/sign_in
```

如果返回正常 HTTP 响应，再检查：

```bash
docker ps
```

确保 GitLab 12 对应的容器正常运行。

## 四、重新运行任务

你刚才的失败已经写入：

```text
runs/shift_analysis/src/per_task.jsonl
```

为了避免后续统计时把环境初始化失败误计为 Agent 任务失败，建议这次使用新的输出目录：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 10 \
  --workers 1 \
  --save-trajectories \
  --out runs/shift_analysis/src_retry1
```

暂时不要在旧目录中混合不同测试结果。

如果任务能进入浏览器交互阶段，说明我们已经解决这次环境变量问题。

接下来才可能出现其他类型的问题，例如 Playwright 浏览器初始化、GitLab 登录、模型 API 调用或 Agent 动作解析。

## 五、建议顺便检查代码中的另一个问题

从当前 `instance.py` 的逻辑来看，它对所有网站进行统一 URL 初始化，增加了不必要的配置依赖。

对于你的研究目标——逐个测试 GitLab 六种环境条件——其实不需要每次加载 Magento 和 WordPress 的地址。

以后可以考虑将：

```python
for site in SITE_NAMES:
    for version in AVAILABLE_VERSIONS:
```

改为按当前任务的网站和版本加载环境变量。

但**现在先不要修改官方源码**，因为我们正处于基础复现阶段，保持代码原样更有利于排查问题。

---

## 六、这次错误对实验结果意味着什么？

你目前得到的：

```text
fail steps=0 skills=0
```

应归类为：

`Infrastructure / Initialization Failure`

而不是：

`Agent Task Failure`

后续实验 A、B 的分析程序也应区分以下状态：

- 环境初始化失败：不纳入有效的 SR 比较，应排障后重跑。
- Agent 正常执行但任务失败：计入失败任务。
- Agent 执行成功：计入成功任务。

特别是在六种条件的配对实验中，如果一个任务在 Src 中初始化失败，而其他条件正常运行，就不能把它当作一次有效的环境变化导致的性能退化。

**你现在直接设置六个环境变量，然后使用 `src_retry1` 重新执行即可。** 这一步不需要更改模型 API，也不需要提前部署另外两个网站。

## 用户

目前来看，可以正常执行了，但是会因为步骤限制失败：
(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$ skillshift run   --agent reference   --site gitlab   --condition src   --tasks skillshift.gitlab.0   --max-steps 10   --workers 1   --save-trajectories   --out runs/shift_analysis/src
running gitlab / src ...
WEBSITE=gitlab
SITE_VERSION=v1
Loading task file: /home/shuyi/projects/SkillShiftBench/skillshift-bench/data/tasks/gitlab/v1.json
Using site URL: http://localhost:8080
/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/beartype/_util/hint/pep/utilpeptest.py:345: BeartypeDecorHintPep585DeprecationWarning: PEP 484 type hint typing.Mapping[str, gymnasium.spaces.space.Space[+_T_co]] deprecated by PEP 585 scheduled for removal in the first Python version released after October 5th, 2025. To resolve this, import this hint from "beartype.typing" rather than "typing". See this discussion for further details and alternatives:
    https://github.com/beartype/beartype#pep-585-deprecations
  warn(
/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/utils/passive_env_checker.py:174: UserWarning: WARN: The obs returned by the `reset()` method is not within the observation space.
  logger.warn(f"{pre} is not within the observation space.")
2026-11-11 17:32:09,920 - HTTP Request: POST https://ark.cn-beijing.volces.com/api/v3/chat/completions "HTTP/1.1 200 OK"
/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/utils/passive_env_checker.py:174: UserWarning: WARN: The obs returned by the `step()` method is not within the observation space.
  logger.warn(f"{pre} is not within the observation space.")
2026-11-11 17:32:12,524 - HTTP Request: POST https://ark.cn-beijing.volces.com/api/v3/chat/completions "HTTP/1.1 200 OK"
....
2026-11-11 17:32:31,712 - HTTP Request: POST https://ark.cn-beijing.volces.com/api/v3/chat/completions "HTTP/1.1 200 OK"
  skillshift.gitlab.v1.0           fail steps=10 skills=0

1 task record(s) written to runs/shift_analysis/src/per_task.jsonl
trajectories/ holds this run's per-step traces (actions, observations, token usage) for local debugging. Same rule as per_task.jsonl: do not commit it, do not attach it anywhere public. It is covered by the repository's .gitignore and is not part of the receipt.
Next: skillshift report runs/shift_analysis/src --out submission/ --name <method> --model <model>

但是我有另一个疑问， 现在我的http://localhost:8080是一个登录界面，我没有任何操作这个界面的历史：
这是测试数据：
{
    "family_id": "skillshift.gitlab.0",
    "legacy_id": "myBenchmark.0",
    "sites": [
      "gitlab"
    ],
    "task_id": 0,
    "require_login": true,
    "storage_state": "./.auth/gitlab_state.json",
    "start_url": "__GITLAB__",
    "geolocation": null,
    "intent_template": "Check out my todos",
    "instantiation_dict": {},
    "intent": "Check out my todos",
    "require_reset": false,
    "eval": {
      "eval_types": [
        "url_match"
      ],
      "reference_answers": null,
      "reference_url": "__GITLAB__/dashboard/todos",
      "program_html": [],
      "url_note": "GOLD in PRED"
    },
    "intent_template_id": 303
  },
如果操作预算足够，是否有可能成功完成任务，并且source和target两个情况下的执行轨迹的确会不同

## ChatGPT

从日志看，模型 API 已经正常响应，任务也进入了实际执行阶段。这个任务的成功条件是到达 GitLab 的 `/dashboard/todos`，但它声明了 `require_login: true` 和登录状态文件，所以我会重点核对自动登录是否生效，以及为什么在登录页面耗尽了 10 步。

## 深度思考

Searched 3 websites

## ChatGPT

**是的，如果增加操作步数，这个任务完全有可能成功；而且 Src 和 Tgt 的执行轨迹也确实可能不同。** 但结合你提供的任务配置和源码，我认为现在应该先确认一个更重要的问题：**Agent 是否已经处于登录状态，以及它在 10 步内究竟做了什么。**

你的日志已经证明基础执行链路正常：

- GitLab 12 网站可以连接。
- Agent 能成功调用火山方舟模型，HTTP 返回 200。
- BrowserGym 能执行任务。
- 任务已经执行了 10 步，没有发生 Python 异常。
- 最终 `success=false`，属于任务未完成，而不是环境初始化失败。

## 一、这个任务实际上很简单

你的任务配置：

```json
{
  "intent": "Check out my todos",
  "require_login": true,
  "start_url": "__GITLAB__",
  "eval": {
    "eval_types": ["url_match"],
    "reference_url": "__GITLAB__/dashboard/todos",
    "url_note": "GOLD in PRED"
  }
}
```

其含义是：

| 字段 | 作用 |
|---|---|
| `intent` | 告诉 Agent 要查看自己的待办事项 |
| `require_login` | 标记任务需要登录 |
| `start_url` | 从 GitLab 网站根路径开始 |
| `eval_types` | 使用 URL 匹配评估 |
| `reference_url` | 目标页面 `/dashboard/todos` |
| `url_note` | 预测 URL 中包含目标 URL 即满足匹配条件 |

也就是说，Agent 最终需要导航至：

```text
http://localhost:8080/dashboard/todos
```

**这个任务不需要创建、修改或删除 GitLab 数据。只要导航到正确页面，就可以满足 URL 评估条件。**

因此，它非常适合作为你当前的基础复现任务。

## 二、为什么你看到登录界面，但没有登录历史？

这里有一个容易混淆的地方。

**你在 Windows 浏览器中访问 `http://localhost:8080`，与 SkillShift-Bench 使用 Playwright 启动的浏览器，是两套独立的浏览器会话。**

<box border radius="lg" padding={3} gap={2}>
  <grid columns={2} gap={3}>
    <grid-item>
      <box background="surface-secondary" padding={3} radius="md" gap={2} align="center">
        <icon name="monitor" size="lg"/>
        **你的 Windows 浏览器**
        <caption textAlign="center">Chrome / Edge</caption>
        <caption textAlign="center">没有登录 Cookie → 显示登录界面</caption>
      </box>
    </grid-item>
    <grid-item>
      <box background="surface-secondary" padding={3} radius="md" gap={2} align="center">
        <icon name="bot" size="lg"/>
        **Agent 的 Playwright 浏览器**
        <caption textAlign="center">由 BrowserGym 启动</caption>
        <caption textAlign="center">执行任务初始化和自动登录</caption>
      </box>
    </grid-item>
  </grid>
  <row justify="center">
    <icon name="arrow-down" color="secondary"/>
  </row>
  <box border radius="md" padding={3} align="center" gap={1}>
    **同一个 GitLab 服务器**
    <text color="secondary" size="xs">`localhost:8080`</text>
  </box>
</box>

### 2.1 SkillShift-Bench 实际上会自动登录

我核对了官方源码：

`src/skillshift/tasks/task.py`

在 `setup()` 中，程序会执行：

```python
for site in self.config["sites"]:
    self.webarena_instance.ui_login(
        site=site,
        version=self.site_version,
        page=page,
    )
```

而 `src/skillshift/tasks/instance.py` 的 `ui_login()` 会在同一个浏览器上下文中新建标签页，进入 GitLab 登录界面，填写预置账号、提交登录，然后关闭登录标签页。

因此，**正常情况下不需要你手动登录，也不需要 Agent 使用自己的 10 步完成登录。** <Cite refs={["turn967227view3","turn289865view0"]}/>

你的配置中虽然有：

```json
"storage_state": "./.auth/gitlab_state.json"
```

但当前这套 SkillShift-Bench 的任务初始化主要使用 `ui_login()`，并不是简单依赖这个文件恢复会话。

### 2.2 但必须确认自动登录真正成功

目前 `ui_login()` 的代码确实会尝试登录，但没有充分检查最终是否仍停留在登录页面。

因此存在一种可能：

- 自动登录脚本没有抛出异常。
- 但 GitLab 登录未真正成功。
- Agent 实际看到的仍然是登录页面。
- 它在 10 步内无法完成任务。

不能仅凭 HTTP 200 和任务能执行就排除这种情况。

---

## 三、首先查看这次 10 步执行轨迹

你已经使用了：

```bash
--save-trajectories
```

因此不需要重新运行，就能检查这次任务实际访问了什么页面、执行了什么动作。

在项目根目录执行：

```bash
python - <<'PY'
import json
from pathlib import Path

p = Path(
    "runs/shift_analysis/src/trajectories/"
    "skillshift.gitlab.v1.0.jsonl"
)

for line in p.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue

    x = json.loads(line)

    print("=" * 60)
    print("Step:", x.get("step"))
    print("URL:", x.get("url"))
    print("Action:", x.get("action"))
    print("Error:", x.get("action_error"))
    print("Reward:", x.get("reward"))
    print("Terminated:", x.get("terminated"))
PY
```

这样你就会得到一个执行过程，例如（仅为示例）：

```text
Step: 0
URL: http://localhost:8080/
Action: click(...)
Reward: 0.0

Step: 1
URL: http://localhost:8080/dashboard
Action: click(...)
Reward: 0.0

Step: 2
URL: http://localhost:8080/dashboard/todos
Action: ...
Reward: 1.0
```

如果成功，通常可以观察到某一步 `reward > 0`。

如果最终仍然是：

```text
http://localhost:8080/users/sign_in
```

就需要优先处理自动登录问题，而不是增加步数。

如果 Agent 一直正常浏览 GitLab，只是没有找到 Todos，那么才需要考虑模型能力或最大操作步数。

注意：轨迹可能包含页面内容、账号信息或其他敏感数据，分享时请先检查并遮挡。

## 四、增加 `--max-steps` 是否可能成功？

完全可能。

但建议先看轨迹，再决定是否增加到 20 或 30 步。

你现在的限制：

```bash
--max-steps 10
```

意味着 Agent 最多执行 10 次动作。

假设它需要：

1. 找到顶部导航。
2. 打开用户相关菜单。
3. 找到 Todos 功能。
4. 进入 Todos 页面。

理论上可能在少量步骤内完成。

但如果模型反复点击错误元素、导航失败或产生无效动作，10 步就可能不够。

确认登录正常后，可以尝试：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 30 \
  --workers 1 \
  --save-trajectories \
  --out runs/shift_analysis/src_30steps
```

我建议暂时使用新的输出目录，保留旧的 10 步轨迹作为调试记录。

在后续六条件正式比较中，必须使用**相同的最大步数**，否则结果不具有可比性。

---

## 五、Src 和 Tgt 的轨迹真的会不同吗？

**是的，而且这正是你的实验重点之一。**

因为 Src 和 Tgt 使用两个不同版本的 GitLab：

| 条件 | GitLab 版本 |
|---|---|
| Src | GitLab 12.0.0 |
| Tgt | GitLab 16.0.6 |

两者在 UI、导航方式、DOM 结构和页面组织上可能存在差异。

例如，Agent 在两个环境中可能产生以下轨迹：

<box border radius="lg" padding={3} gap={3}>
  <grid columns={2} gap={3}>
    <grid-item>
      <text weight="medium" size="sm">Src：GitLab 12</text>
      <box border radius="md" padding={2} gap={2}>
        <box background="surface-secondary" radius="sm" padding={2} align="center">
          <text size="xs">GitLab 首页</text>
        </box>
        <row justify="center"><icon name="arrow-down" color="secondary"/></row>
        <box background="surface-secondary" radius="sm" padding={2} align="center">
          <text size="xs">导航菜单 A</text>
        </box>
        <row justify="center"><icon name="arrow-down" color="secondary"/></row>
        <box background="surface-secondary" radius="sm" padding={2} align="center">
          <text size="xs">Todos 页面</text>
        </box>
      </box>
    </grid-item>
    <grid-item>
      <text weight="medium" size="sm">Tgt：GitLab 16</text>
      <box border radius="md" padding={2} gap={2}>
        <box background="surface-secondary" radius="sm" padding={2} align="center">
          <text size="xs">GitLab 首页</text>
        </box>
        <row justify="center"><icon name="arrow-down" color="secondary"/></row>
        <box background="surface-secondary" radius="sm" padding={2} align="center">
          <text size="xs">新导航菜单 B</text>
        </box>
        <row justify="center"><icon name="arrow-down" color="secondary"/></row>
        <box background="surface-secondary" radius="sm" padding={2} align="center">
          <text size="xs">Todos 页面</text>
        </box>
      </box>
    </grid-item>
  </grid>
  <caption>示意图：两种版本的中间操作可能不同，具体路径需要由实际轨迹确认。</caption>
</box>

对于你这个任务，两个版本最终可能都达到 `/dashboard/todos`，但它们的中间交互步骤、观察内容和动作选择可能明显不同。

不过要注意，**不同版本不保证轨迹一定不同**。

如果两个版本都支持直接导航到相同 URL，Agent 也可能使用完全相同的动作完成任务。

另外，即使两个环境没有变化，LLM 本身的随机性也可能造成轨迹不同。因此，一次 Src 和一次 Tgt 的轨迹不同，不能直接证明差异完全由环境变化造成。

这也是我建议后续增加重复运行和环境结构分析的原因。

---

## 六、针对你的实验 A、B，我有一个新的建议

你当前选择的任务 `skillshift.gitlab.0` 是一个非常好的基础连通性测试任务，但它可能不适合作为衡量所有环境变化的代表性任务。

原因是它只需要访问一个页面：

```text
/dashboard/todos
```

而且采用 URL 匹配评分。

如果 Agent 通过 `goto()` 直接导航到这个页面：

- 可以绕开很多导航 UI 变化。
- 可能不需要依赖 CSS Selector 或复杂 DOM。
- 也可能不容易暴露特定的执行扰动。
- 只要最终 URL 符合要求，评分器就可能判定成功。

所以，**它适合验证实验流程，却不适合单独代表五种 Shift 的难度。**

建议你将任务分成两类：

| 任务类别 | 作用 |
|---|---|
| 简单导航任务（当前任务） | 验证登录、模型 API、BrowserGym 和评分系统 |
| 多步骤交互任务 | 正式测量 DOM 变化、执行障碍和任务性能退化 |

后续可以选择需要创建 Issue、修改配置、填写表单或执行多个页面操作的任务族，并保持 Src/Tgt 任务目标对齐。

这样你才能真正观察到 Perceptual Shift 和 Execution Shift 对 Agent 行为的影响。

---

## 七、现在最推荐的下一步

**先不要立即运行六种条件，也不要急着部署复杂的实验 A 采集器。**

你已经有一份完整的 Src 10 步轨迹，我们应该先利用它判断失败原因。

请先执行我在第三部分提供的轨迹分析代码，把输出中的以下内容发给我：

- 10 步的 URL。
- 10 步的 Action。
- 对应 Error 和 Reward。

我可以据此具体判断：

1. 自动登录是否正常。
2. Agent 是否卡在登录页面。
3. 模型是否正确理解任务。
4. 是否确实需要将 `max-steps` 增加到 30。
5. 这个任务是否适合作为后续 Src 与 Tgt 轨迹比较的初始样本。

**你现在不缺少网站或模型配置，最有价值的是搞清楚这 10 步具体失败在哪里。**

## 用户

Step: 0
URL: http://localhost:8080/
Action: ```
Error: 
Reward: 0.0
Terminated: False
从第一步到第9步都是：
Step: 9
URL: http://localhost:8080/
Action: ```
Error: ValueError: Received an empty action.
Reward: 0.0
Terminated: False

## 深度思考

Searched 11 websites

## ChatGPT

现在可以明确定位失败原因了：**不是 `--max-steps 10` 太小，而是 Agent 输出的动作格式不正确，导致 BrowserGym 连续 10 次没有执行有效操作。**

你提供的轨迹有三个关键信号：

```text
Step: 0
URL: http://localhost:8080/
Action: ```
Error:
Reward: 0.0
Terminated: False
```

以及：

```text
Step: 9
URL: http://localhost:8080/
Action: ```
Error: ValueError: Received an empty action.
Reward: 0.0
Terminated: False
```

这意味着：

1. **URL 始终没变化**：Agent 没有成功导航到其他页面。
2. **Action 是三个反引号 ` ``` `**：高度怀疑模型输出的 Markdown 代码块没有被正确解析。
3. **出现 `Received an empty action`**：BrowserGym 收到的动作内容为空，无法执行。

所以即使将最大步数从 10 提高到 30，也很可能只是重复失败 30 次。

目前最值得怀疑的是你使用的 DeepSeek 模型与 SkillShift-Bench `reference` Agent 的动作输出格式之间存在兼容性问题。

但还不能直接认定是模型本身的问题，需要进一步确认模型实际回复了什么，以及 Reference Agent 如何解析回复。

## 一、已经定位到 Reference Agent 的动作解析问题

我核对了官方 `src/skillshift/agents/reference.py`，发现了一个与你的现象高度吻合的代码问题。

官方 Agent 的系统提示词要求模型：

```text
Reply with a short reason, then the single next action in a fenced code block.
```

也就是类似：

````text
I should navigate to the Todos page.

```python
goto("http://localhost:8080/dashboard/todos")
```
````

然后使用 `extract_action()` 从模型回复中提取动作。

核心代码是：

```python
_FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

def extract_action(text: str):
    match = _FENCE_RE.search(text or "")
    if match:
        action = match.group(1).strip()
        if action:
            return action

    lines = [
        line.strip()
        for line in (text or "").splitlines()
        if line.strip()
    ]
    if not lines:
        raise SkillShiftError("The model returned no action")

    return lines[-1]
```

问题就在最后一行：

```python
return lines[-1]
```

如果模型回复的格式与正则要求不完全一致，比如代码块前后有额外字符，正则没有匹配成功，程序就会直接取回复的最后一行。

当最后一行恰好为：

```text
```
```

Agent 就会把三个反引号当作浏览器动作发送出去。这和你看到的执行轨迹完全吻合。<Cite ref="turn970727view0"/>

但目前还不能确认模型到底输出了什么：可能是代码块格式不兼容，也可能是模型只生成了不完整的代码块。

**因此，我们先检查模型原始回复，而不是立即修改 Benchmark 或增加最大步数。**

## 二、第一步：检查模型实际输出

在项目根目录执行下面的测试。它使用和 Reference Agent 相同的 OpenAI SDK、模型配置及温度，并提供一个简单的模拟浏览器观察。

```bash
python - <<'PY'
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["my_api_key"],
    base_url=os.environ["my_base_url"],
)

response = client.chat.completions.create(
    model=os.environ["my_model"],
    temperature=0,
    messages=[
        {
            "role": "system",
            "content": (
                "You are a web agent operating a browser.\n"
                "Available actions: goto(url), click(bid), "
                "fill(bid, value), scroll(dx, dy).\n"
                "Reply with a short reason, then the single next "
                "action in a fenced code block."
            )
        },
        {
            "role": "user",
            "content": (
                "# Goal\nCheck out my todos\n"
                "# Current URL\nhttp://localhost:8080/\n"
                "# Accessibility tree\n"
                "- link 'Todos': /dashboard/todos"
            )
        }
    ]
)

message = response.choices[0].message

print("=== RAW CONTENT ===")
print(repr(message.content))

print("\n=== REASONING CONTENT ===")
print(repr(getattr(message, "reasoning_content", None)))

print("\n=== FINISH REASON ===")
print(response.choices[0].finish_reason)

print("\n=== TOKEN USAGE ===")
print(response.usage)
PY
```

这是一次独立的模型 API 测试，不会操作 GitLab 网站。

重点观察：

- `content` 是否包含 `goto(...)` 或 `click(...)`。
- 是否只有 ``` 这样的 Markdown 标记。
- 是否存在 `reasoning_content`，而 `content` 很短。
- `finish_reason` 是否为 `length`，表示生成可能被截断。

如果这里已经输出不完整的代码块，就需要优先处理模型生成格式。

如果这里输出正确，说明还需要检查完整任务中较长的 Accessibility Tree 是否影响了模型输出。

## 三、第二步：直接验证动作解析器

不用再次调用模型，可以先在当前环境运行：

```bash
python - <<'PY'
from skillshift.agents.reference import extract_action

samples = {
    "标准代码块": 'I will navigate.\n```python\ngoto("http://localhost:8080/dashboard/todos")\n```',
    "单行代码块": '```python goto("http://localhost:8080/dashboard/todos") ```',
    "没有语言标记": '```\ngoto("http://localhost:8080/dashboard/todos")\n```',
}

for name, reply in samples.items():
    try:
        print(name, "=>", repr(extract_action(reply)))
    except Exception as e:
        print(name, "=> ERROR:", e)
PY
```

如果第二个样例返回的是 `'```python goto(...) ```'`，而不是 `goto(...)`，就证明解析器对某些格式不够健壮。

### 接下来怎样修复？

我建议采用最小改动，不去修改任务、扰动机制和评分器。

首先在 `reference.py` 中，定位：

```python
reply = self._completion(self._build_messages(obs))
action = extract_action(reply)
```

临时增加一行用于调试：

```python
reply = self._completion(self._build_messages(obs))

print("DEBUG MODEL RAW REPLY:", repr(reply))

action = extract_action(reply)
```

这样再次运行时，你就能看到模型返回的完整 `content`，判断解析错误发生在哪一步。

注意：完整模型回复可能包含网页文本或敏感信息，不要直接公开完整日志，排查后记得移除这行调试代码。

## 四、根据结果选择修复方案

| 观察结果 | 原因方向 | 解决策略 |
|---|---|---|
| 模型输出完整动作，但格式不标准 | 动作解析器过于严格 | 改进 `extract_action()` |
| 模型返回空内容 | 模型输出或 API 参数兼容问题 | 检查 `reasoning_content` 和生成参数 |
| 模型只输出不完整代码块 | 生成截断或格式遵循失败 | 调整生成设置及提示词 |
| 模型输出正确，解析也正确 | 可能是 BrowserGym 动作格式问题 | 检查 `env.step()` 和动作错误 |
| 模型持续回复无效动作 | 模型与 Agent 的动作协议不匹配 | 试用其他模型或更严格的动作输出约束 |

对于你的环境变化研究，我建议最终使用一个能稳定输出 BrowserGym 原始动作的模型。否则六种环境下的失败主要反映的是**模型动作格式兼容性**，而不是网站演化带来的影响。

而且，在正式比较六种条件之前，应固定动作解析器版本、模型配置和提示词，确保实验公平。

## 五、目前不建议做的事情

- 不要直接把 `--max-steps` 提高到 30 或 50。当前问题并非预算不足。
- 不要为了让任务成功而修改 `per_task.jsonl` 或评分函数。
- 不要开始运行六种环境。先确保 Src 能成功执行有效动作。
- 不要根据现在的 `fail steps=10` 计算环境鲁棒性指标，因为这些是动作解析失败导致的无效步骤。

**下一步请先运行第二部分的模型原始输出测试，把 `RAW CONTENT`、`REASONING CONTENT`、`FINISH REASON` 和 Token Usage 的输出发给我（删除其中可能包含的密钥或敏感信息）。**

有了这些信息，就能判断是 DeepSeek 模型输出不完整、推理内容与正文分离，还是 Reference Agent 的正则解析逻辑需要修改。

## 用户

的确是解析的问题，请修复这个bug，使解析更加健壮：
=== RAW CONTENT ===
"The page has a Todos link; I'll navigate to it directly.\n\n```action\ngoto(http://localhost:8080/dashboard/todos)\n```"

=== REASONING CONTENT ===
'The goal is "Check out my todos" and the current URL is localhost:8080/. The accessibility tree shows a link "Todos" at /dashboard/todos. I should click that link.\n\nI need to find the bid for the link, but the accessibility tree doesn\'t include bids explicitly. The action requires a bid. Since only one element is listed, I\'ll assume bid 1. But let me be careful—maybe navigating directly is safer. Actually, the link points to /dashboard/todos, so I could just goto that URL directly. But clicking the link is more natural. Since I don\'t have a bid, I\'ll use goto.\n\nLet me use goto to navigate to the todos page.'

=== FINISH REASON ===
stop

=== TOKEN USAGE ===
CompletionUsage(completion_tokens=176, prompt_tokens=111, total_tokens=287, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=None, audio_tokens=None, reasoning_tokens=145, rejected_prediction_tokens=None, text_tokens=None), prompt_tokens_details=PromptTokensDetails(audio_tokens=None, cache_write_tokens=None, cached_tokens=0, image_tokens=None, text_tokens=None))
(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$ python - <<'PY'
from skillshift.agents.reference import extract_action

samples = {
    "标准代码块": 'I will navigate.\n```python\ngoto("http://localhost:8080/dashboard/todos")\n```',
    "单行代码块": '```python goto("http://localhost:8080/dashboard/todos") ```',
    "没有语言标记": '```\ngoto("http://localhost:8080/dashboard/todos")\n```',
}

for name, reply in samples.items():
    try:
        print(name, "=>", repr(extract_action(reply)))
    except Exception as e:
        print(name, "=> ERROR:", e)
PY
标准代码块 => 'goto("http://localhost:8080/dashboard/todos")'
单行代码块 => '```python goto("http://localhost:8080/dashboard/todos") ```'
没有语言标记 => 'goto("http://localhost:8080/dashboard/todos")'

## ChatGPT

你给出的原始回复已经能确定两个问题：解析器不识别 ```action 代码块，而且模型生成的 `goto(http://...)` 缺少 URL 字符串引号。我会按“提取动作 → 规范化可修复的语法 → 拒绝不安全或不明确的输出”设计修复，并附上可直接运行的测试。

## 深度思考

Patching action parsing
Patched action parsing

## 深度思考

Searched 10 websites

## ChatGPT

根据你的实际模型输出，以及官方 `reference.py` 的实现，现在可以确定需要修复两个 Bug：

| 问题 | 模型实际输出 | 原解析器的行为 |
|---|---|---|
| 代码块语言标记不兼容 | ` ```action ` | 只识别 ` ```python ` 或无标记 |
| URL 参数没有引号 | `goto(http://localhost:8080/dashboard/todos)` | 即使提取成功，也不是合法的 Python 动作 |

我建议**只修改 Reference Agent 的动作解析器，不修改 SkillShift-Bench 的任务、环境扰动及评分代码**。

修复后的解析器应当具备以下能力：

1. 识别 `python`、`action`、无语言标记和单行代码块。
2. 自动修复 `goto(http://...)` 缺少引号的问题。
3. 提取有效的单个 BrowserGym 动作。
4. 使用 Python AST 检查动作语法，但不执行模型生成的代码。
5. 对无法识别的回复明确报错，避免继续把 ``` 当作动作执行。

这样可以保证你后续比较 Src、Src-Perc、Src-Exec、Tgt 等条件时，使用的是同一个稳定的动作协议。

## 一、修改 `reference.py`

你当前的项目文件：

```text
~/projects/SkillShiftBench/skillshift-bench/src/skillshift/agents/reference.py
```

先备份：

```bash
cd ~/projects/SkillShiftBench/skillshift-bench

cp src/skillshift/agents/reference.py \
   src/skillshift/agents/reference.py.bak
```

打开：

```bash
code src/skillshift/agents/reference.py
```

找到原来的：

```python
_FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

def extract_action(text: str) -> Action:
    ...
```

将 `_FENCE_RE` 和整个 `extract_action()` 函数替换为下面这段代码。文件顶部另外增加 `import ast`。

<text weight="medium">修复后的解析器</text>

<CodeBlock language="python" editable>
import ast

_FENCE_RE = re.compile(r"```(.*?)```", re.DOTALL)
_LANGUAGE_RE = re.compile(
    r"^(?:python|py|action|browsergym)(?:\s+|$)",
    re.IGNORECASE,
)
_BARE_URL_RE = re.compile(
    r"^goto\(\s*(https?://[^\s'\"()]+)\s*\)$"
)

_ALLOWED_ACTIONS = {
    "click",
    "fill",
    "hover",
    "select_option",
    "keyboard_press",
    "scroll",
    "goto",
    "go_back",
    "go_forward",
    "new_tab",
    "tab_focus",
    "tab_close",
    "send_msg_to_user",
    "report_infeasible",
}


def _normalize_action(candidate: str) -> str:
    """Normalize and validate one BrowserGym action."""
    candidate = candidate.strip().rstrip(";").strip()

    # Repair only an unquoted HTTP(S) URL in goto(...).
    match = _BARE_URL_RE.fullmatch(candidate)
    if match:
        candidate = f"goto({match.group(1)!r})"

    try:
        tree = ast.parse(candidate, mode="exec")
    except SyntaxError as exc:
        raise SkillShiftError(
            f"Invalid action syntax: {candidate!r}"
        ) from exc

    # Exactly one top-level function call is allowed.
    if len(tree.body) != 1:
        raise SkillShiftError("Expected exactly one action")

    statement = tree.body[0]
    if not isinstance(statement, ast.Expr):
        raise SkillShiftError("Expected a function call")

    call = statement.value
    if not isinstance(call, ast.Call):
        raise SkillShiftError("Expected a function call")

    if not isinstance(call.func, ast.Name):
        raise SkillShiftError("Unsupported action expression")

    if call.func.id not in _ALLOWED_ACTIONS:
        raise SkillShiftError(
            f"Unknown browser action: {call.func.id}"
        )

    # Reject nested function calls, attribute access,
    # assignments and other executable expressions.
    for argument in [*call.args, *(kw.value for kw in call.keywords)]:
        for node in ast.walk(argument):
            if isinstance(
                node,
                (
                    ast.Call,
                    ast.Attribute,
                    ast.Lambda,
                    ast.NamedExpr,
                    ast.Await,
                    ast.Yield,
                    ast.YieldFrom,
                    ast.ListComp,
                    ast.SetComp,
                    ast.DictComp,
                    ast.GeneratorExp,
                ),
            ):
                raise SkillShiftError(
                    "Complex expressions are not valid action arguments"
                )

    # Return a valid Python action, never execute it here.
    return candidate


def extract_action(text: str) -> Action:
    """Extract one valid action from a model response."""
    if not text or not text.strip():
        raise SkillShiftError("The model returned an empty reply")

    candidates = []

    # Prefer fenced code blocks.
    for match in _FENCE_RE.finditer(text):
        body = match.group(1).strip()

        # Strip optional language marker:
        # ```python, ```action, ```browsergym, etc.
        body = _LANGUAGE_RE.sub("", body, count=1).strip()

        if body:
            candidates.append(body)

    # Fallback for models that omit code fences.
    if not candidates:
        for line in reversed(text.splitlines()):
            line = line.strip()
            if re.match(
                r"^[a-zA-Z_]\w*\s*\(",
                line,
            ):
                candidates.append(line)

    errors = []
    for candidate in candidates:
        try:
            return _normalize_action(candidate)
        except SkillShiftError as exc:
            errors.append(str(exc))

    raise SkillShiftError(
        "No valid browser action found in model response. "
        + "; ".join(errors[:3])
    )
</CodeBlock>

这份代码与原来的一个重要区别是：**它不会在无法解析代码块时盲目返回最后一行。**

它也不会使用 `eval()` 或 `exec()` 执行模型输出。

需要说明的是，AST 检查只是一层语法及动作形式的验证，不是完整的浏览器操作沙箱；真正的元素 ID、参数类型以及页面状态仍由 BrowserGym 判断。

## 二、同时加强 Agent 的输出提示词

仅修复解析器已经可以解决你当前遇到的情况，但建议再做一个小改动，减少模型以后生成非法动作的概率。

在同一个 `reference.py` 中找到 `SYSTEM_PROMPT`。

原来只要求模型返回 fenced code block，没有明确要求使用 Python 字符串语法。

建议替换为：

<CodeBlock language="python" editable>
SYSTEM_PROMPT = """You are a web agent operating a browser through a fixed action space.

Available actions:
{actions}

Rules:
- Choose exactly ONE browser action per response.
- Give a short reason, followed by one fenced code block.
- Use ```python for the code block.
- The code block must contain exactly one valid Python function call.
- Always quote string arguments with single or double quotes.
- For URLs, write goto("https://example.com/path"), never goto(https://example.com/path).
- Use only the available browser actions.
- Use element IDs from the current accessibility tree.
- Do not invent element IDs.
- Do not output multiple actions or explanatory comments inside the code block.
- When the task asks for an answer, use send_msg_to_user(...).
"""
</CodeBlock>

这样模型就会收到更明确的格式约束。

例如：

````text
I should navigate to the Todos page.

```python
goto("http://localhost:8080/dashboard/todos")
```
````

需要注意，**更改提示词本身也可能影响 Agent 的行为**。对于你的环境变化研究，应将这个修复后的版本固定为同一个实验配置，六种条件全部使用它，不要与之前未修复的运行结果混合比较。

## 三、验证修复结果

修改后，先执行 Python 语法检查：

```bash
python -m py_compile \
  src/skillshift/agents/reference.py
```

然后运行下面这组测试，不调用模型 API，也不启动浏览器。

<CodeBlock language="bash" editable>
python - <<'PY'
from skillshift.agents.reference import extract_action

tests = {
    "标准 Python 代码块": (
        'Reason\n```python\nclick("42")\n```',
        'click("42")'
    ),
    "Action 代码块": (
        'Reason\n```action\ngoto(http://localhost:8080/dashboard/todos)\n```',
        "goto('http://localhost:8080/dashboard/todos')"
    ),
    "无语言标记": (
        '```\nclick("7")\n```',
        'click("7")'
    ),
    "单行代码块": (
        '```python goto("http://localhost:8080/dashboard/todos") ```',
        'goto("http://localhost:8080/dashboard/todos")'
    ),
    "无代码块": (
        'I will click the button.\nclick("42")',
        'click("42")'
    ),
    "双引号 URL": (
        '```action\ngoto("http://localhost:8080/dashboard/todos")\n```',
        'goto("http://localhost:8080/dashboard/todos")'
    ),
}

for name, (input_text, expected) in tests.items():
    actual = extract_action(input_text)
    assert actual == expected, (
        f"{name}: expected {expected!r}, got {actual!r}"
    )
    print(f"PASS: {name} -> {actual}")

print("\nAll valid-action tests passed.")
PY
</CodeBlock>

预期：

```text
PASS: 标准 Python 代码块 -> click("42")
PASS: Action 代码块 -> goto('http://localhost:8080/dashboard/todos')
PASS: 无语言标记 -> click("7")
PASS: 单行代码块 -> goto("http://localhost:8080/dashboard/todos")
PASS: 无代码块 -> click("42")
PASS: 双引号 URL -> goto("http://localhost:8080/dashboard/todos")

All valid-action tests passed.
```

再测试非法动作能否被正确拒绝：

<CodeBlock language="bash" editable>
python - <<'PY'
from skillshift.agents.reference import extract_action

invalid_cases = [
    "```",
    "",
    "I am thinking about what to do next.",
    "```python\nclick('1')\nclick('2')\n```",
    "```python\nunknown_action('x')\n```",
    "```python\n__import__('os').system('echo test')\n```",
]

for text in invalid_cases:
    try:
        result = extract_action(text)
        raise AssertionError(
            f"Unexpectedly accepted: {result!r}"
        )
    except AssertionError:
        raise
    except Exception as exc:
        print(f"PASS: Rejected invalid action ({type(exc).__name__})")

print("\nInvalid-action tests passed.")
PY
</CodeBlock>

如果全部通过，就能确认你这次遇到的代码块解析和 URL 引号问题已被修复。

## 四、重新执行 GitLab Src 任务

确认测试通过后，运行：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 10 \
  --workers 1 \
  --save-trajectories \
  --out runs/shift_analysis/src_parser_fixed
```

使用新目录是为了保留之前解析失败的轨迹，同时避免旧数据进入后续统计。

完成后检查：

```bash
cat runs/shift_analysis/src_parser_fixed/per_task.jsonl
```

再查看轨迹中的动作：

```bash
python - <<'PY'
import json
from pathlib import Path

root = Path("runs/shift_analysis/src_parser_fixed/trajectories")

for path in root.glob("*.jsonl"):
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        x = json.loads(line)
        print(
            f"Step {x.get('step')}: "
            f"URL={x.get('url')} | "
            f"Action={x.get('action')} | "
            f"Error={x.get('action_error')}"
        )
PY
```

### 如何判断修复成功？

| 运行结果 | 说明 |
|---|---|
| `success=true` | 动作解析、网站操作和任务评分链路已跑通 |
| `success=false`，但动作有效 | 解析器已经修复，需要继续分析 Agent 决策 |
| 仍出现 `Action: ``` ` | 修改没有生效，或代码仍走旧解析路径 |
| `No valid browser action found` | 模型返回了无法安全解析的动作，需要检查实际输出 |

## 五、对后续六条件实验的影响

建议你将当前修复视为一个明确的实验版本：

```text
Agent: ReferenceReActAgent
Model: deepseek-v4-1-flash-economy-261017
Action parser: robust-v1
Temperature: 0
Skill: disabled
```

另外，保存一下修改后的 Git diff：

```bash
git diff -- src/skillshift/agents/reference.py
```

这有助于将来复现实验。

有一个细节尤其需要记住：**本次修复只保证动作格式尽量合法，不保证模型选择的动作一定正确。** 例如 `goto()` 的 URL 即使格式合法，仍然可能指向错误页面。

对于你要研究的五种环境变化，建议后续把错误分成两类：动作格式错误和真实交互失败。前者通常是 Agent 接口问题，后者才更可能反映环境变化对任务执行造成的影响。

**下一步目标：先让 `skillshift.gitlab.0` 在修复后的 Reference Agent 下完成一次成功执行，再使用同一份解析器和提示词测试 Src-Perc、Src-Exec、Tgt 等其他条件。**

## 用户

我在另一个分支上直接修改了代码，暂时没有改system prompt;
但是现在出现了新的错误：
(.venv) shuyi@DESKTOP-7HNQ7U2:~/projects/SkillShiftBench/skillshift-bench$ skillshift run   --agent reference   --site gitlab   --condition src   --tasks skillshift.gitlab.0   --max-steps 10   --workers 1   --save-trajectories   --out runs/shift_analysis/src
running gitlab / src ...
WEBSITE=gitlab
SITE_VERSION=v1
Loading task file: /home/shuyi/projects/SkillShiftBench/skillshift-bench/data/tasks/gitlab/v1.json
Using site URL: http://localhost:8080
/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/beartype/_util/hint/pep/utilpeptest.py:345: BeartypeDecorHintPep585DeprecationWarning: PEP 484 type hint typing.Mapping[str, gymnasium.spaces.space.Space[+_T_co]] deprecated by PEP 585 scheduled for removal in the first Python version released after October 5th, 2025. To resolve this, import this hint from "beartype.typing" rather than "typing". See this discussion for further details and alternatives:
    https://github.com/beartype/beartype#pep-585-deprecations
  warn(
/home/shuyi/projects/SkillShiftBench/skillshift-bench/.venv/lib/python3.12/site-packages/gymnasium/utils/passive_env_checker.py:174: UserWarning: WARN: The obs returned by the `reset()` method is not within the observation space.
  logger.warn(f"{pre} is not within the observation space.")
2026-11-11 18:17:30,362 - HTTP Request: POST https://ark.cn-beijing.volces.com/api/v3/chat/completions "HTTP/1.1 200 OK"
2026-11-11 18:17:30,371 - Task skillshift.gitlab.v1.0 failed during execution
Traceback (most recent call last):
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/src/skillshift/runner.py", line 131, in run_task
    action = agent.act(obs)
             ^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/src/skillshift/agents/reference.py", line 318, in act
    action = extract_action(reply)
             ^^^^^^^^^^^^^^^^^^^^^
  File "/home/shuyi/projects/SkillShiftBench/skillshift-bench/src/skillshift/agents/reference.py", line 206, in extract_action
    raise SkillShiftError(
skillshift.errors.SkillShiftError: No valid browser action found in model response. Expected exactly one action
  skillshift.gitlab.v1.0           fail steps=0 skills=0

1 task record(s) written to runs/shift_analysis/src/per_task.jsonl
trajectories/ holds this run's per-step traces (actions, observations, token usage) for local debugging. Same rule as per_task.jsonl: do not commit it, do not attach it anywhere public. It is covered by the repository's .gitignore and is not part of the receipt.
Next: skillshift report runs/shift_analysis/src --out submission/ --name <method> --model <model>

## 深度思考

Searched 6 websites

## ChatGPT

这次错误和上一次不同，但实际上说明我们已经向前推进了一步：

**之前：** 解析器把 ` ``` ` 当成浏览器动作，导致 BrowserGym 连续执行无效操作。

**现在：** 新解析器识别到了模型响应中的候选动作，但因为不符合“只能包含一个动作”的规则，主动抛出了异常。

关键报错是：

```text
skillshift.errors.SkillShiftError:
No valid browser action found in model response.
Expected exactly one action
```

发生位置：

```text
reference.py → extract_action(reply)
```

并且：

```text
fail steps=0 skills=0
```

这说明错误发生在第一次模型调用之后、第一次浏览器动作执行之前。

### 当前最可能的原因

你没有修改 System Prompt，而原始提示词只要求模型在代码块中输出下一步动作。模型可能返回了：

````text
I should navigate to the Todos page.

```action
goto("http://localhost:8080/dashboard/todos")
# Navigate to the Todos page
```
````

或者：

````text
```action
goto("http://localhost:8080/dashboard/todos")
click("12")
```
````

这两种格式都会被之前提供的解析器拒绝，因为 `ast.parse()` 会解析出多个顶层语句。

不过，**目前还没有看到这次模型的原始回复，因此不能确定是哪一种情况**。也可能是代码块中存在自然语言、额外的 Markdown 标记或其他格式问题。

我建议先查看原始回复，再采取最小范围的修复，不要直接删除多动作校验。

## 一、先获取这次真正的模型回复

在你当前分支的 `reference.py` 中，找到 `act()` 方法，大约在第 318 行：

```python
action = extract_action(reply)
```

在它之前加入：

```python
print("\n========== RAW MODEL REPLY ==========")
print(repr(reply))
print("=====================================\n")

action = extract_action(reply)
```

修改后重新运行，使用新目录：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 10 \
  --workers 1 \
  --save-trajectories \
  --out runs/shift_analysis/src_debug
```

这次即使第一步失败，也会在终端显示模型实际返回的内容。

**特别注意：不要把整个 Accessibility Tree 或包含登录凭证的 Prompt 打印出来，只需要 `reply`。**

---

## 二、建议进一步增强解析器：允许注释，但严格保持单动作

上次给你的解析器使用：

```python
if len(tree.body) != 1:
    raise SkillShiftError("Expected exactly one action")
```

这个检查本身是合理的。对于真正的多动作回复，不应该自动执行其中的第一条，因为这样会悄悄改变 Agent 的行为。

但是，我们可以让解析器忽略代码块中的注释、说明文字，并正确处理多个候选代码块。

特别是之前的：

```python
for candidate in candidates:
    try:
        return _normalize_action(candidate)
```

它会在找到第一个合法候选后立即返回。若模型输出多个不同动作，就可能产生歧义。

对于你的实验，我更推荐保留明确的单动作约束，并在解析失败时输出候选动作的简短摘要。

你可以先把 `extract_action()` 中原来的错误汇总部分：

```python
raise SkillShiftError(
    "No valid browser action found in model response. "
    + "; ".join(errors[:3])
)
```

替换为：

```python
raise SkillShiftError(
    "No valid browser action found in model response.\n"
    f"Candidate count: {len(candidates)}\n"
    f"Errors: {errors[:3]!r}\n"
    f"Candidate previews: {[c[:200] for c in candidates[:3]]!r}"
)
```

这样，即使程序失败，也能知道：

- 提取到了几个候选代码块。
- 哪个代码块包含多个语句。
- 是否存在注释、自然语言或额外动作。

对于包含纯 Python 注释的代码块，`ast.parse()` 本身不会将注释计为一条语句，因此无需额外删除注释。

如果模型输出：

```python
goto("http://localhost:8080/dashboard/todos")
click("12")
```

则应该继续拒绝，并通过提示词或重新生成机制让模型只输出一条动作。

---

## 三、我建议最终采用的修复策略

你要研究五种环境变化，因此我更推荐以下解析优先级：

| 回复形式 | 处理方式 |
|---|---|
| ` ```python` + 单动作 | 接受 |
| ` ```action` + 单动作 | 接受 |
| 无语言标记代码块 + 单动作 | 接受 |
| 单行代码块 + 单动作 | 接受 |
| `goto(http://...)` | 修复 URL 引号后接受 |
| 代码块中含 Python 注释 | 接受 |
| 代码块中含两条动作 | 拒绝，提示模型重新生成 |
| 无代码块但有明确单动作 | 接受 |
| 只有自然语言或空代码块 | 拒绝 |
| 多个互相冲突的动作候选 | 拒绝 |

如果后续需要进一步提高稳定性，可以采用 **一次格式修复重试**：当解析失败时，将模型原回复和解析错误重新提交给模型，要求只返回一个合法动作。重试次数和模型调用费用都应该记录，并且六种条件使用一致的设置。

现阶段不必立即实现重试，先确定此次实际输出即可。

---

## 四、为什么不建议直接修改 System Prompt？

你当前没有修改 System Prompt，这没有问题。先保持不变，能让我们单独观察解析器的效果。

但是，如果最终发现模型经常输出多个动作，那么需要修改提示词或增加格式重试。否则无论解析器多么健壮，都不能可靠地把多个动作变成一个有效动作。

对于你的环境变化研究，我建议把实验实现划分为：

- **Parser v1**：接受各种代码块格式，修复明确的 URL 引号问题。
- **Agent Prompt v1**：保留原始 Reference Agent 提示词。
- **Parser v2（可选）**：失败时增加一次格式修复重试。

不要把不同解析器版本的任务结果混在同一份 SR 统计中。

## 五、下一步

当前最重要的不是继续更改 `--max-steps`，而是获取这次模型响应：

```python
print("RAW MODEL REPLY:", repr(reply))
```

然后把实际输出发给我。

根据输出，我可以进一步判断究竟是：

1. 模型在同一个代码块中返回了多个动作。
2. 模型生成了自然语言和动作混合的代码块。
3. 新解析器把单行代码块错误拆开。
4. 模型生成了其他 BrowserGym 格式。

**只有确认实际回复后，才能做针对性修复，而不引入影响后续环境变化实验的新行为。**

## 用户

这是本次输出：
logger.warn(f"{pre} is not within the observation space.")
2026-11-11 18:28:22,339 - HTTP Request: POST https://ark.cn-beijing.volces.com/api/v3/chat/completions "HTTP/1.1 200 OK"

========== RAW MODEL REPLY ==========
'I’ll open the Todos page from the dashboard navigation.\n\n```json\n{"action":"click","bid":"169"}\n```'
=====================================

## ChatGPT

现在找到真正原因了。**这次不是多动作问题，而是 DeepSeek 模型返回了 JSON 格式的动作，但我们之前的解析器只接受 Python 函数调用。**

你的模型输出：

````text
I’ll open the Todos page from the dashboard navigation.

```json
{"action":"click","bid":"169"}
```
````

这是一个有效的动作意图，但不是 BrowserGym 直接执行的 Python 代码。

我们需要做的是增加一个 **JSON → BrowserGym Action 转换层**。

## 一、为什么会报错？

当前解析器从代码块提取到：

```json
{"action":"click","bid":"169"}
```

然后交给：

```python
ast.parse(candidate, mode="exec")
```

JSON 对象被解析为 Python 字典表达式，而非函数调用，因此触发：

```text
Expected exactly one action
```

正确处理后，应转换为：

```python
click("169")
```

再交给 BrowserGym 执行。

## 二、推荐的修复方案

保留你目前的 `_normalize_action()` 和 `extract_action()`，增加 JSON 格式识别。

首先在 `reference.py` 顶部添加：

```python
import json
```

然后添加下面两个辅助函数。

<CodeBlock language="python" editable>
def _json_to_action(text: str) -> str:
    """Convert a JSON action object to a BrowserGym action."""

    data = json.loads(text)

    if not isinstance(data, dict):
        raise SkillShiftError("JSON action must be an object")

    name = data.get("action")

    if not isinstance(name, str):
        raise SkillShiftError("JSON action name must be a string")

    # Start with the actions relevant to the current failure.
    if name == "click":
        bid = data.get("bid")
        if not isinstance(bid, (str, int)):
            raise SkillShiftError("click requires a bid")
        return f"click({str(bid)!r})"

    if name == "goto":
        url = data.get("url")
        if not isinstance(url, str):
            raise SkillShiftError("goto requires a URL")
        if not url.startswith(("http://", "https://")):
            raise SkillShiftError("goto requires an HTTP(S) URL")
        return f"goto({url!r})"

    if name == "fill":
        bid = data.get("bid")
        value = data.get("value")
        if not isinstance(bid, (str, int)):
            raise SkillShiftError("fill requires a bid")
        if not isinstance(value, str):
            raise SkillShiftError("fill requires a string value")
        return f"fill({str(bid)!r}, {value!r})"

    if name == "scroll":
        dx = data.get("dx")
        dy = data.get("dy")
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in (dx, dy)
        ):
            raise SkillShiftError("scroll requires numeric dx and dy")
        return f"scroll({dx!r}, {dy!r})"

    raise SkillShiftError(f"Unsupported JSON action: {name!r}")


def _parse_candidate(candidate: str) -> str:
    candidate = candidate.strip()

    if candidate.startswith("{"):
        try:
            converted = _json_to_action(candidate)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise SkillShiftError(
                f"Invalid JSON action: {exc}"
            ) from exc
        return _normalize_action(converted)

    return _normalize_action(candidate)
</CodeBlock>

这里有两个设计原则：

- 使用白名单转换 JSON 动作，不直接执行模型返回的任意 JSON 内容。
- 转换后仍然经过你原来的 `_normalize_action()` 验证。

这样不会破坏对 Python 动作的支持。

## 三、修改 `extract_action()` 的两处代码

### 3.1 让代码块语言识别支持 JSON

找到：

```python
_LANGUAGE_RE = re.compile(
    r"^(?:python|py|action|browsergym)(?:\s+|$)",
    re.IGNORECASE,
)
```

修改为：

```python
_LANGUAGE_RE = re.compile(
    r"^(?:python|py|action|browsergym|json)(?:\s+|$)",
    re.IGNORECASE,
)
```

这样就可以从：

````text
```json
{"action":"click","bid":"169"}
```
````

中提取 JSON 对象。

### 3.2 修改候选动作解析调用

在 `extract_action()` 中找到：

```python
for candidate in candidates:
    try:
        return _normalize_action(candidate)
    except SkillShiftError as exc:
        errors.append(str(exc))
```

修改为：

```python
for candidate in candidates:
    try:
        return _parse_candidate(candidate)
    except SkillShiftError as exc:
        errors.append(str(exc))
```

注意：只修改调用函数，不需要删除原先的 `_normalize_action()`。

---

## 四、测试 JSON 和 Python 动作是否都能正常解析

修改完成后执行：

```bash
python -m py_compile src/skillshift/agents/reference.py
```

然后测试：

<CodeBlock language="python" editable>
from skillshift.agents.reference import extract_action

tests = {
    "JSON click": (
        '```json\n{"action":"click","bid":"169"}\n```',
        "click('169')"
    ),
    "JSON goto": (
        '```json\n{"action":"goto","url":"http://localhost:8080/dashboard/todos"}\n```',
        "goto('http://localhost:8080/dashboard/todos')"
    ),
    "JSON fill": (
        '```json\n{"action":"fill","bid":"15","value":"hello"}\n```',
        "fill('15', 'hello')"
    ),
    "Python action": (
        '```python\nclick("169")\n```',
        'click("169")'
    ),
    "Unquoted URL": (
        '```action\ngoto(http://localhost:8080/dashboard/todos)\n```',
        "goto('http://localhost:8080/dashboard/todos')"
    ),
}

for name, (text, expected) in tests.items():
    actual = extract_action(text)
    assert actual == expected, (
        f"{name}: expected={expected!r}, actual={actual!r}"
    )
    print(f"PASS: {name} => {actual}")

print("All tests passed.")
</CodeBlock>

可以将代码放到终端的 Python heredoc 中执行，或者保存为独立测试文件。

预期：

```text
PASS: JSON click => click('169')
PASS: JSON goto => goto('http://localhost:8080/dashboard/todos')
PASS: JSON fill => fill('15', 'hello')
PASS: Python action => click("169")
PASS: Unquoted URL => goto('http://localhost:8080/dashboard/todos')
All tests passed.
```

## 五、是否需要修改 System Prompt？

**目前不一定需要。**

既然 DeepSeek 有时输出 Python，有时输出 JSON，我们可以先让解析器兼容两种格式，从而减少因格式差异导致的无效动作。

但是，这并不代表混用两种输出协议是最理想的长期方案。

对于正式研究，我建议在基础运行成功后，将 Prompt 固定为 Python BrowserGym 动作格式，并保留 JSON 兼容解析作为容错机制。

更严格的实验方案是让模型始终按照一种动作格式输出，然后记录格式违规次数。

这样可以进一步区分：

- 模型动作生成失败。
- 动作解析失败。
- 浏览器实际交互失败。
- 环境变化导致的任务失败。

---

## 六、重新运行 GitLab 测试

测试通过后，执行：

```bash
skillshift run \
  --agent reference \
  --site gitlab \
  --condition src \
  --tasks skillshift.gitlab.0 \
  --max-steps 10 \
  --workers 1 \
  --save-trajectories \
  --out runs/shift_analysis/src_json_fixed
```

这次如果模型返回：

```json
{"action":"click","bid":"169"}
```

解析器会转换成：

```python
click('169')
```

然后由 BrowserGym 尝试点击元素 `169`。

**需要注意：解析成功不代表点击一定成功。** 如果当前页面不存在 `bid=169`，BrowserGym 仍然可能报告元素不存在；那属于 Agent 动作选择问题，而不是解析问题。

最后提醒：你目前选择的模型在相邻两次运行中返回了两种完全不同的动作格式。这说明在进入六条件正式实验之前，最好先固定系统提示词和动作协议，否则格式随机性可能成为环境变化分析中的干扰因素。

**下一步目标是让 `skillshift.gitlab.0` 至少出现一次真实有效的浏览器动作，而不是立即追求 `success=true`。** 完成后，我们再检查 Agent 是否登录、如何导航，以及 Src 与其他环境条件的实际轨迹差异。
