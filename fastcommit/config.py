"""
配置管理模块
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class APIConfig:
    """API 配置类"""

    api_base: str = "https://api.deepseek.com/"
    api_key: str = ""
    model: str = "deepseek-reasoner"
    language: str = "en"


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        # 将配置保存在 fastcommit 模块目录下
        self.config_dir = Path(__file__).parent
        self.config_file = self.config_dir / "user_config.json"

    def load_config(self) -> APIConfig:
        """加载配置"""
        # 从配置文件读取
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    return APIConfig(**config_data)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"配置文件格式错误: {e}")
                print("将使用默认配置")

        # 返回默认配置
        return APIConfig()

    def save_config(self, config: APIConfig):
        """保存配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(asdict(config), f, indent=2, ensure_ascii=False)
        except PermissionError:
            print(f"❌ 无法写入配置文件: {self.config_file}")
            print("请检查文件权限或以管理员身份运行")
            raise

    def is_configured(self) -> bool:
        """检查是否已配置"""
        if not self.config_file.exists():
            return False
        config = self.load_config()
        return bool(config.api_key and config.api_key != "")

    def setup_first_time(self) -> APIConfig:
        """首次运行时的配置设置"""
        print("=" * 50)
        print("🚀 欢迎使用 FastCommit!")
        print("=" * 50)
        print("首次运行需要配置 API 信息")
        print()
        print("📖 DeepSeek API 文档: https://api-docs.deepseek.com/zh-cn/")
        print("💡 您可以在上述链接中申请 API Key 并查看模型信息")
        print()

        # 获取用户输入
        print("请输入以下信息:")

        # API Base URL
        api_base = input(f"API Base URL (默认: https://api.deepseek.com/): ").strip()
        if not api_base:
            api_base = "https://api.deepseek.com/"

        # API Key
        api_key = ""
        while not api_key:
            api_key = input("API Key (必填): ").strip()
            if not api_key:
                print("❌ API Key 不能为空，请重新输入")
                print("💡 请访问 https://platform.deepseek.com/api_keys 申请 API Key")

        # Model
        model = input(f"模型名称 (默认: deepseek-reasoner): ").strip()
        if not model:
            model = "deepseek-reasoner"

        # Language
        language = input(f"语言 (默认: en): ").strip()
        if not language:
            language = "en"

        # 创建配置
        config = APIConfig(api_base=api_base, api_key=api_key, model=model, language=language)

        # 保存配置
        try:
            self.save_config(config)
            print()
            print("✅ 配置已保存!")
            print(f"📁 配置文件位置: {self.config_file}")
            print("=" * 50)
            print()
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            print("请检查文件权限或以管理员身份运行")
            raise

        return config

    def get_config_info(self) -> Dict:
        """获取配置信息摘要"""
        config = self.load_config()

        return {
            "api_base": config.api_base,
            "model": config.model,
            "language": config.language,
            "api_key_configured": bool(config.api_key),
            "api_key_preview": f"{config.api_key[:8]}..." if config.api_key else "未配置",
            "config_file": str(self.config_file),
        }

    def update_config_interactive(self):
        """交互式更新配置"""
        config = self.load_config()

        print("当前配置:")
        print(f"  API Base URL: {config.api_base}")
        print(f"  API Key: {config.api_key[:8]}..." if config.api_key else "  API Key: 未设置")
        print(f"  模型: {config.model}")
        print(f"  语言: {config.language}")
        print()

        # API Base URL
        new_base = input(f"新的 API Base URL (当前: {config.api_base}, 回车跳过): ").strip()
        if new_base:
            config.api_base = new_base

        # API Key
        new_key = input(f"新的 API Key (当前: {'已设置' if config.api_key else '未设置'}, 回车跳过): ").strip()
        if new_key:
            config.api_key = new_key

        # Model
        new_model = input(f"新的模型名称 (当前: {config.model}, 回车跳过): ").strip()
        if new_model:
            config.model = new_model

        # Language
        new_language = input(f"新的语言 (当前: {config.language}, 回车跳过): ").strip()
        if new_language:
            config.language = new_language

        # 保存配置
        try:
            self.save_config(config)
            print("✅ 配置已更新!")
        except Exception as e:
            print(f"❌ 更新配置失败: {e}")
            print("请检查文件权限或以管理员身份运行")
            raise

        return config
