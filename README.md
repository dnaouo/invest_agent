# A股投资Agent系统

基于 LangGraph 编排的多智能体半自动投资信号系统。LLM 使用 Kimi K2.6，数据源为 tushare Pro + akshare。

投资目标：年最大回撤 ≤20%，年化跑赢沪深300 + 5%。

## 安装

```bash
# 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 安装项目（开发模式）
pip install -e ".[dev]"
```

## 环境变量

复制 `.env.example` 为 `.env`，填入真实凭证：

```bash
cp .env.example .env
```

需要配置：
- `MOONSHOT_API_KEY` — Kimi API 密钥
- `TUSHARE_TOKEN` — tushare Pro 数据接口 token

## 运行测试

```bash
pytest
```
