# 经验沉淀

每次子 agent 遇到的坑和解决方案记录在此。后续子 agent 启动前必读。

格式：`### YYYY-MM-DD 问题简述` + 正文描述问题和解决方案。

---

### 2026-05-02 pip install -e . 需要先执行才能跑测试

Phase 0a 子 agent 创建完代码后，首次运行 pytest 报 `ModuleNotFoundError: No module named 'tenacity'`。原因是 pyproject.toml 声明了依赖但没有执行 `pip install -e ".[dev]"`。后续每次 Phase 新增依赖后，必须重新执行安装。

### 2026-05-02 PowerShell 不支持 bash 语法

Windows 环境下 PowerShell 不支持 `mkdir -p`、`&&` 等 bash 语法。目录创建用 `New-Item -ItemType Directory -Force`，命令串联用 `;` 而不是 `&&`。

### 2026-05-02 控制台中文编码

PowerShell 输出中文会乱码（GBK vs UTF-8），但不影响实际功能。如果需要看中文输出，用 `python script.py` 重定向到文件再读。

### 2026-05-02 pytest 找不到 src 下的包

**问题**：`pyproject.toml` 通过 `[tool.setuptools.package-dir] "" = "src"` 把 src 作为包根，但 `pytest` 直接运行时无法 import `vault` 等包，报 `ModuleNotFoundError`。

**解决**：在 `[tool.pytest.ini_options]` 中添加 `pythonpath = ["src"]`，让 pytest 自动把 src 加入 `sys.path`。

### 2026-05-02 python-decouple 需要显式安装

**问题**：`pyproject.toml` 声明了 `python-decouple` 依赖，但如果没做 `pip install -e .`，直接 `python -m pytest` 会因缺少 decouple 失败。

**解决**：确保运行测试前已 `pip install python-decouple`（或 `pip install -e .[dev]`）。

### 2026-05-02 router 路由表不能用模块级静态函数引用

**问题**：`router.py` 如果在模块加载时用 `_ROUTES = {"get_daily": tushare_client.get_daily}` 保存函数引用，测试中 `patch("sandboxes.data.tushare_client.get_daily")` 无法影响已存入字典的引用，导致 mock 失效。

**解决**：路由表只存字符串名称，`execute()` 中用 `getattr(tushare_client, api_name)` 动态获取，这样 patch 模块属性就能生效。

### 2026-05-02 PowerShell 不支持 && 连接符

**问题**：Windows PowerShell（非 pwsh 7+）不支持 `&&` 连接命令，会报 `InvalidEndOfLine` 错误。

**解决**：用分号 `;` 分隔命令，或升级到 PowerShell 7+。

### 2026-05-02 tenacity 需要显式安装

**问题**：`pyproject.toml` 声明了 `tenacity` 依赖，但如果没做 `pip install -e .`，直接跑 pytest 会因缺少 tenacity 失败。

**解决**：确保 `pip install tenacity`（或 `pip install -e .`）。与 python-decouple 同理，所有 pyproject.toml 中声明的运行时依赖在首次环境搭建时都需要安装。

### 2026-05-02 PowerShell 不支持 && 连接符

**问题**：在 PowerShell 中使用 `cd xxx && python -m pytest` 会报 `InvalidEndOfLine` 错误。

**解决**：在 PowerShell 中用分号 `;` 分隔命令，或者使用 Shell 工具的 `working_directory` 参数指定工作目录。

### 2026-05-02 akshare 财联社快讯接口名变更

**问题**：任务文档中指定的 `ak.stock_zh_a_alerts_cls()` 在当前版本 akshare 中不存在，运行时报 `AttributeError`。

**解决**：用 `dir(ak)` 搜索发现正确接口名为 `ak.stock_info_global_cls()`（对应财联社电报 https://www.cls.cn/telegraph）。akshare 接口名会随版本变化，使用前应先通过 `dir()` 或 `help()` 确认实际可用的函数名。

### 2026-05-02 批量扩展 tushare_client 遵循模板复制模式

**经验**：扩展 tushare_client.py 时，12 个新函数严格复制 get_income 的模式（@retry 装饰器 + _get_pro() 在 try 外 + 统一返回格式），无需发明新抽象。测试同样复制已有 test 的 mock 模式（autouse fixture 重置 _pro + patch get_credential + patch ts.pro_api）。保持模式一致性比 DRY 更重要——后续维护者能一眼看懂每个函数。

### 2026-05-02 DuckDB SQL 列名不能用单引号

**问题**：在 DuckDB 的 INSERT 语句中，列名用 Python `repr()` 生成的单引号 `'col_name'` 会报 `ParserException`，DuckDB 要求标识符用双引号 `"col_name"`。

**解决**：列名引用统一用 `f'"{col}"'` 格式化，不要用 `repr()` 或 `!r`。

### 2026-05-02 akshare 返回的 DataFrame 列名是中文

**问题**：`ak.stock_zh_a_alerts_cls()` 返回的列名是 `['标题', '内容', '发布日期', '发布时间']`，不是英文。DuckDB upsert 时 key_columns 必须匹配实际列名，否则报 BinderException。

**解决**：在入库前检查实际列名，或统一做列名映射。Phase 0b 暂时用中文列名作为 key。

### 2026-05-02 akshare 无金十快讯专用接口

**问题**：任务要求用 `ak.js_news` 获取金十快讯，但当前版本 akshare 中不存在该接口。`dir(ak)` 中 `js_` 前缀的函数只有 `crypto_js_spot`、`stock_js_weibo_nlp_time`、`stock_js_weibo_report`、`stock_zyjs_ths`，均非金十快讯。

**解决**：`get_jin10_news` 函数内部用 `hasattr(ak, "js_news")` 做防御检查，不存在时 fallback 到 `ak.stock_info_global_sina()`（新浪全球快讯，列名为 `时间/内容`）。如果后续 akshare 版本新增金十接口，代码会自动优先使用。

### 2026-05-02 多源新闻聚合需做字段映射

**问题**：CLS 财联社返回列名 `['标题', '内容', '发布日期', '发布时间']`，Sina 新浪返回列名 `['时间', '内容']`，列名不同且均为中文。直接合并会导致字段不一致。

**解决**：在 `news_aggregator.py` 中为每个源定义映射字典（如 `_CLS_FIELD_MAP`、`_SINA_FIELD_MAP`），统一映射到英文字段 `title/content/time/date/source`。缺失字段（如 Sina 无 title）从 content 截取前 60 字符填充。

### 2026-05-02 tushare get_npr 只传非空参数

**问题**：`pro.npr()` 如果传空字符串参数（如 `org=""`），tushare 可能按空字符串过滤导致结果为空。

**解决**：在 `get_npr` 内用条件判断，只把非空参数放入 kwargs 字典再 `**kwargs` 展开传给 API，而不是把所有参数都传过去。这个模式适用于所有可选参数的 tushare 接口。

### 2026-05-02 DuckDB :memory: 连接池需清理

**问题**：`duckdb_store` 使用 `_connections` 字典缓存连接。测试用 `:memory:` 时，如果不在 fixture 中清理 `_connections`，后续测试可能拿到已被关闭或已有数据的连接，导致测试不隔离。

**解决**：在 `autouse` fixture 的 yield 后执行 `duckdb_store._connections.clear()`，确保每个测试用例使用全新的内存数据库。

### 2026-05-02 StrReplace 追加代码时必须匹配文件真正的末尾

**问题**：`tushare_client.py` 在其他 Phase 子 agent 并行扩展后，文件末尾比当前 agent 首次读取时更长（多了 Research Report / Policy Agent 部分）。用 StrReplace 匹配旧末尾位置追加代码，结果代码被插到了中间而非真正的文件末尾，导致 `import` 时找不到新函数。

**解决**：追加代码前，重新 Read 文件确认实际末尾内容，用文件真正最后一段代码作为 `old_string` 来做 StrReplace。

### 2026-05-02 Batch API 测试用 monkeypatch 替换模块常量

**问题**：`kimi_batch.py` 用模块级 `_BATCH_DIR` 控制 JSONL 存储路径，测试中需要写临时目录。

**解决**：用 `monkeypatch.setattr(_mod, "_BATCH_DIR", tmp_path / "batch_jobs")` 替换路径常量，比 mock Path 更简洁且覆盖真实文件 I/O。同样适用于 `_MAX_LINES` 等数值常量的边界测试。

### 2026-05-02 Session events 测试需清理 duckdb_store._connections

**问题**：`session/events.py` 通过 `_get_conn(":memory:")` 获取 DuckDB 内存连接。测试 fixture 只清理了 `_INITIALIZED` 字典，但 `duckdb_store._connections` 中缓存的 `:memory:` 连接未清理，导致多个测试共享同一内存数据库，`test_get_events_filter` 因前序测试残留数据而失败（期望 1 条 llm_call 事件，实际拿到 2 条）。

**解决**：在 `autouse` fixture 的 setup 和 teardown 中同时执行 `duckdb_store._connections.pop(":memory:", None)`，确保每个测试用例拿到独立的内存数据库连接。这与之前 DuckDB `:memory:` 连接池清理的经验一致。

### 2026-05-02 Langfuse 可观测性接入需要模块级状态重置

**问题**：`langfuse_client.py` 使用模块级全局变量 `_langfuse` 和 `_disabled` 做懒加载和降级标记。测试之间如果不重置这两个变量，前一个测试的降级状态会污染后续测试。

**解决**：在 `autouse` fixture 的 setup 和 teardown 中显式重置 `mod._langfuse = None` 和 `mod._disabled = False`。这是模块级单例/缓存的通用测试模式。

### 2026-05-02 langfuse 4.x SDK 安装会带入 opentelemetry 依赖树

**经验**：`pip install langfuse` (v4.5.1) 会额外安装 `opentelemetry-api/sdk/exporter-otlp-proto-http`、`protobuf`、`googleapis-common-protos`、`wrapt`、`backoff` 等依赖。如果项目有 protobuf 版本冲突需注意。目前无冲突。

### 2026-05-02 DuckDB ORDER BY ts 在快速连续插入时排序不稳定

**问题**：`time.time()` 精度有限，极快连续调用 `emit_event` 时多条记录的 `ts` 值相同，导致 `ORDER BY ts DESC LIMIT 1` 返回不确定的行。`wake` 函数的 `last_event_type` / `last_agent` 因此不可靠。

**解决**：在 ORDER BY 中加 `rowid DESC` 作为 tiebreaker：`ORDER BY ts DESC, rowid DESC LIMIT 1`。DuckDB 的 `rowid` 按插入顺序递增，保证相同 `ts` 时仍能取到最后插入的行。

### 2026-05-02 Fundamental Agent mock 模式：patch 模块而非函数引用

**经验**：`fund.py` 中用 `tushare_client.get_income(...)` 而非 `from sandboxes.data.tushare_client import get_income` 直接导入函数。这样测试中 `@patch("agents.fund.tushare_client")` 可以一次 mock 整个模块，所有 `getattr(mock_ts, "get_xxx")` 自动生效。如果改为导入具体函数，则需要逐个 `@patch("agents.fund.get_income")`，更繁琐且容易遗漏。这与 learnings 中 "router 路由表不能用模块级静态函数引用" 的经验一脉相承。

### 2026-05-02 Critic Agent JSON 解析需强制覆盖 verdict

**问题**：LLM 返回的 JSON 中 `verdict` 字段可能与 `score` 不一致（例如 score=35 但 LLM 写了 verdict="pass"）。

**解决**：解析 JSON 后，根据 `score >= 60` 强制重算 `verdict`，不信任 LLM 自行判断的 verdict 值。这是 GAN 模式下的防御性编程——Critic 的通过/拒绝阈值必须由代码控制，不能让 LLM 自由发挥。

### 2026-05-02 LangGraph StateGraph + TypedDict 兼容性良好

**经验**：LangGraph 的 `StateGraph` 可以直接接受 `TypedDict(total=False)` 作为 state schema，无需额外适配。`graph.compile()` 返回可执行图，`graph.invoke(initial_state)` 传入初始状态后返回完整的最终状态（含所有节点写入的 key）。Phase 1a 最简编排 `fund -> critic -> END` 只需 5 行核心代码。测试时 mock 各节点的外部依赖（tushare_client、call_kimi）即可，不需要 mock LangGraph 本身。

### 2026-05-02 Batch Agent 创建严格复制 fund.py 模式

**经验**：创建 Macro/Tech/Event 三个 agent 时，严格复制 `fund.py` 的代码结构（_PROMPT_PATH + _load_prompt + _fetch_data + xxx_node）效率最高。区别仅在于：(1) Macro agent 不需要 ts_code 参数，只需 trade_date；(2) 多数据源 agent（如 Macro）同时 import tushare_client 和 akshare_client；(3) 测试中对多模块 mock 用 `@patch` 叠加装饰器，注意参数顺序与装饰器顺序相反。

### 2026-05-02 Batch 2 Agent（Flow/Risk/Backtest）同样复制 fund.py 模式

**经验**：第二批 4 个 agent（flow_institutional、flow_hot_money、risk、backtest）严格复制相同模式，零障碍一次通过。关键区别：(1) flow_institutional 的 `_fetch_data` 中 `get_moneyflow_hsgt` 不需要 ts_code，只传 start_date/end_date；(2) risk agent 调三个接口（pledge_stat + stk_holdertrade + share_float），fallback 中需包含 position_suggestion 默认值避免下游 KeyError；(3) backtest agent 用 trade_date 减 600 天覆盖约 120 个交易日，比精确计算交易日历更简洁。

### 2026-05-03 Sprint Contract 复用 handoff.py 的文件 I/O 模式

**经验**：`sprint_contract.py` 的 `generate_contract` / `load_contract` 完全复用 `handoff.py` 的 `save_handoff` / `load_handoff` 模式——Pydantic model + `model_dump_json` 写入 + `json.loads` 读回 + `contract_dir` 可注入参数（测试用 `tmp_path`）。LLM 返回 JSON 解析用 `content.index("{")` / `content.rindex("}")` 提取 JSON 子串，失败时降级到默认值。这个"提取 JSON + 降级 fallback"的模式可复用到后续所有需要 LLM 输出结构化数据的场景。

### 2026-05-03 slice_data 缺失字段默认行为需显式排除

**问题**：`slice_data` 用 `r.get(date_field, "")` 时，缺少 date_field 的记录会得到空字符串 `""`，而 `"" <= "20250510"` 为 True，导致缺失日期的记录被保留——这是 look-ahead 漏洞。

**解决**：改用 `r.get(date_field) is not None` 前置检查，None 时直接排除。`slice_financial` 同理。凡是做时间截断的过滤器，都必须把缺失字段视为"不可信数据"丢弃而非保留。

### 2026-05-03 safe_run_node 降级模式无需 mock LangGraph

**经验**：`fallback.py` 的 `safe_run_node` 是纯函数包装器（接收 node_func + state + fallback_key），与 LangGraph 编排解耦。测试时直接传入普通函数即可，无需 mock StateGraph 或 compile。pass^k 测试中 mock `tools.pass_k.run_analysis`（即 mock 导入处）而非 `harness.orchestrator.run_analysis`（定义处），符合 "patch where it's looked up" 原则。

### 2026-05-03 Dashboard 聚合查询复用 session events 的 :memory: 连接

**经验**：`dashboard.py` 的 `generate_daily_report` 直接通过 `_get_conn(db_path)` 访问 DuckDB，与 `session/events.py` 共享连接池。测试中先用 `emit_event(..., db_path=":memory:")` 写入数据，再用 `generate_daily_report(..., db_path=":memory:")` 读取，两者通过 `_connections` 字典拿到同一个内存连接，无需额外 setup。清理 fixture 同时清 `_connections` 和 `_INITIALIZED`。

### 2026-05-03 浮点精度断言用 pytest.approx

**问题**：`(0.8 + 0.6 + 0.7 + 0.5) / 4` 在 Python 中不严格等于 `0.65`（浮点精度），导致 `assert result == expected` 失败。

**解决**：用 `pytest.approx(0.65, abs=1e-9)` 做近似比较。所有涉及浮点运算的断言都应使用 `pytest.approx`。

### 2026-05-05 SQLite :memory: 每次 connect 产生独立数据库

**问题**：与 DuckDB 不同，`sqlite3.connect(":memory:")` 每次调用都会创建一个全新的独立内存数据库。如果多个函数各自调 `_get_conn(":memory:")`，它们拿到的是不同数据库，跨函数写入/读取无法共享数据，导致测试中 `get_portfolio` 读不到 `update_portfolio` 写入的数据。

**解决**：测试中改用 `tmp_path / "test.sqlite"` 临时文件作为 `db_path`，pytest 的 `tmp_path` fixture 自动清理。这比实现连接缓存更简单，且与生产环境（文件型 SQLite）行为一致。

### 2026-05-05 pnl_report.py 模块级 import 需要在测试中提前 mock

**问题**：`pnl_report.py` 有 `from sandboxes.data import tushare_client`，虽然函数体内未使用，但模块加载时会触发 tushare_client 的初始化链。测试中若不 mock，会因缺少 `.env` 中的 tushare token 而失败。

**解决**：在 `test_pnl_report.py` 中用 `with patch("tools.pnl_report.tushare_client"):` 包裹 import 语句，在模块加载前拦截。这种 "patch-before-import" 模式适用于所有带副作用模块级 import 的测试场景。

### 2026-05-05 daily_runner 中 mock 外部调用的正确位置

**经验**：`daily_runner.py` 导入了 `run_analysis`、`emit_event`、`write_note` 等多个外部函数。测试中 patch 的目标是 `harness.daily_runner.run_analysis`（导入处）而非 `harness.orchestrator.run_analysis`（定义处）。所有 7 个外部依赖全部 patch 后测试秒过，无需真实数据库或 API。

### 2026-05-06 V2-A 批量扩展 tushare_client 第三批 13 个接口

**经验**：第三批扩展（moneyflow_ind_ths/cnt_ths、fina_mainbz、stk_holdernumber、forecast_vip、express_vip、limit_list_d、margin/margin_detail、hsgt_top10、top10_holders、moneyflow、index_daily）继续严格复制已有模式，一次通过。可选参数函数用 kwargs 构造 + 只传非空值的模式已成标准做法。测试中为可选参数函数额外写一个 `_no_optional_success` 用例，验证不传可选参数时 kwargs 中不含该 key。
