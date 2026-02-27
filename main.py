"""
Deep Research Agent - 通用任务入口

零领域知识：所有领域逻辑由 plugins 提供，core 只做通用调度。
"""

import asyncio
import argparse
from pathlib import Path

from core.config import load_app_config
from core.registry import get_registry


class TaskSystem:
    """通用任务系统"""

    def __init__(self, config_path=None):
        self.config = load_app_config(config_path)
        self._registry = get_registry()
        self._registry.auto_discover(['plugins', 'core'])

    async def chat_execute(self, message: str, history: list = None) -> str:
        """通过 LLM + tool-use 执行任务（使用 ToolUseRunner）"""
        from core.chat_router import _get_llm_client, _get_system_prompt, execute_tool, get_all_tools
        from core.tool_use_runner import ToolUseRunner

        client, model = _get_llm_client()
        messages = [{"role": m["role"], "content": m["content"]} for m in (history or [])]
        messages.append({"role": "user", "content": message})

        runner = ToolUseRunner(
            client=client,
            model=model,
            system_prompt=_get_system_prompt(),
            tools=get_all_tools(),
            execute_tool=execute_tool,
            on_text=lambda text: print(text),
            on_tool_call=lambda name, _: print(f"  → {name}"),
        )
        return await runner.run(messages)

    async def interactive(self):
        """交互式 chat 循环"""
        print("\n🚀 Deep Research Agent")
        print("=" * 50)
        print("输入任务描述，AI 自动编排执行。输入 quit 退出。")
        print("=" * 50)

        history = []
        while True:
            try:
                user_input = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break

            if user_input.strip().lower() in ('quit', 'exit', 'q'):
                print("再见！")
                break

            if not user_input.strip():
                continue

            response = await self.chat_execute(user_input, history)
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})

    def start_server(self):
        """启动 FastAPI 服务"""
        import uvicorn
        uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


async def main():
    parser = argparse.ArgumentParser(
        description="Deep Research Agent - 通用任务系统"
    )
    parser.add_argument(
        'task', nargs='?', default=None,
        help='任务描述（自然语言），由 LLM 编排执行'
    )
    parser.add_argument(
        '--config', type=str, default='config/config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '--server', action='store_true',
        help='启动 FastAPI 服务 (port 8000)'
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists() and config_path.name != 'config.yaml':
        print(f"⚠️  配置文件不存在: {config_path}，将使用默认配置")
        config_path = None

    system = TaskSystem(config_path)

    if args.server:
        system.start_server()
    elif args.task:
        await system.chat_execute(args.task)
    else:
        await system.interactive()


if __name__ == "__main__":
    asyncio.run(main())
