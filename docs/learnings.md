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
