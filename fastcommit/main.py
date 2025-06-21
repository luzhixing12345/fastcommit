"""
FastCommit 命令行入口
"""

import argparse
import sys
import json
from .core import FastCommit, OpenAIProvider
from .config import ConfigManager, APIConfig


def show_config_help():
    """显示配置帮助信息"""
    print(
        """
配置 FastCommit API：

方法1: 交互式配置 (推荐)
fsc config

方法2: 使用配置命令
fsc config --api-key your_api_key_here
fsc config --api-base https://api.deepseek.com/
fsc config --model deepseek-reasoner
fsc config --language en

查看当前配置:
fsc config --show
"""
    )


def configure_api(args):
    """配置 API"""
    config_manager = ConfigManager()

    # 显示当前配置
    if args.show:
        config_info = config_manager.get_config_info()
        print("当前配置:")
        for key, value in config_info.items():
            print(f"  {key}: {value}")
        return

    # 加载现有配置
    config = config_manager.load_config()

    # 更新配置
    if args.api_key:
        config.api_key = args.api_key
        print("API Key 已更新")

    if args.api_base:
        config.api_base = args.api_base
        print(f"API Base URL 已更新为: {args.api_base}")

    if args.model:
        config.model = args.model
        print(f"模型已更新为: {args.model}")

    if args.language:
        config.language = args.language
        print(f"语言已更新为: {args.language}")

    # 如果没有提供任何参数，进入交互式配置
    if not any([args.api_key, args.api_base, args.model, args.language, args.show]):
        config = config_manager.update_config_interactive()

    # 保存配置
    if any([args.api_key, args.api_base, args.model, args.language]) or not args.show:
        config_manager.save_config(config)
        print(f"配置已保存到: {config_manager.config_file}")


def show_staged_files():
    """显示暂存区文件"""
    try:
        fc = FastCommit()
        summary = fc.get_staged_files_summary()

        if "error" in summary:
            print(f"错误: {summary['error']}")
            return

        if "message" in summary:
            print(summary["message"])
            return

        print(f"暂存区文件 ({summary['total_files']} 个):")
        for change in summary["changes"]:
            print(f"  {change['type']}: {change['file']}")

    except Exception as e:
        print(f"错误: {e}")


def generate_commit_message():
    """生成 commit message"""
    try:
        # 加载配置
        config_manager = ConfigManager()

        # 检查是否首次运行
        if not config_manager.is_configured():
            print("检测到首次运行，需要配置 API 信息...")
            config = config_manager.setup_first_time()
        else:
            config = config_manager.load_config()

        # 验证配置
        if not config.api_key:
            print("错误: API Key 未配置")
            print("\n请先配置 API:")
            show_config_help()
            return

        # 创建 AI 提供者 (这里需要根据实际的AI提供者类进行调整)
        # 假设使用 OpenAI 兼容的接口
        ai_provider = OpenAIProvider(api_key=config.api_key, base_url=config.api_base, model=config.model)

        # 创建 FastCommit 实例
        fc = FastCommit(ai_provider)

        # 显示暂存区修改文件
        print("正在分析暂存区修改...")

        # 获取并显示修改的文件
        summary = fc.get_staged_files_summary()
        if "error" in summary:
            print(f"错误: {summary['error']}")
            return
        if "message" in summary:
            print(summary["message"])
            return

        # 用绿色显示修改的文件
        print(f"\n修改的文件 ({summary['total_files']} 个):")
        for change in summary["changes"]:
            # ANSI 绿色代码: \033[32m, 重置代码: \033[0m
            print(f"  \033[32m{change['type']}: {change['file']}\033[0m")

        # 生成 commit message
        print("\n生成的 Commit Message:")
        print("=" * 50)

        # 流式生成并显示
        commit_msg = fc.generate_commit_message(language=config.language)

        print("=" * 50)

        # 询问是否直接提交
        while True:
            choice = input("\n是否使用此消息进行提交？ (y/n/e): ").lower().strip()

            if choice == "y":
                import subprocess

                try:
                    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                    print("✅ 提交成功!")
                except subprocess.CalledProcessError as e:
                    print(f"❌ 提交失败: {e}")
                break
            elif choice == "n":
                print("已取消提交")
                break
            elif choice == "e":
                import subprocess

                try:
                    # 先使用当前消息进行提交
                    print(f"\n正在提交当前消息...")
                    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                    print("✅ 提交成功!")

                    # 然后调用 git commit --amend 进入编辑模式
                    print("正在打开编辑器修改提交信息...")
                    subprocess.run(["git", "commit", "--amend"], check=True)
                    print("✅ 提交信息已更新!")

                except subprocess.CalledProcessError as e:
                    print(f"❌ 操作失败: {e}")
                break
            else:
                print("请输入 y (提交)、n (取消) 或 e (编辑)")

    except Exception as e:
        print(f"错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FastCommit - AI 生成 Git Commit Message",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  fsc                    # 生成 commit message
  fsc status            # 查看暂存区状态
  fsc config            # 配置 API
  fsc config --show     # 查看当前配置
        """,
    )

    parser.add_argument("--version", "-v", action="store_true", help="显示版本信息")

    # 配置子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # status 子命令
    status_parser = subparsers.add_parser("status", help="显示暂存区文件状态")

    # config 子命令
    config_parser = subparsers.add_parser("config", help="配置 API 设置")
    config_parser.add_argument("--api-key", help="设置 API Key")
    config_parser.add_argument("--api-base", help="设置 API Base URL")
    config_parser.add_argument("--model", help="设置使用的模型")
    config_parser.add_argument("--language", help="设置语言")
    config_parser.add_argument("--show", action="store_true", help="显示当前配置")

    args = parser.parse_args()

    # 处理版本信息
    if args.version:
        from . import __version__

        print(f"FastCommit v{__version__}")
        return

    # 处理子命令
    if args.command == "config":
        configure_api(args)
        return

    # 处理状态查看
    if args.command == "status":
        show_staged_files()
        return

    # 默认行为：生成 commit message
    generate_commit_message()


if __name__ == "__main__":
    main()
