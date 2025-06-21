"""
FastCommit 核心功能实现
"""

import subprocess
import os
import sys
from typing import List, Dict, Optional, Tuple
import json
from dataclasses import dataclass

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("请先安装 OpenAI SDK: pip install openai")


@dataclass
class GitChange:
    """Git 修改信息"""

    file_path: str
    change_type: str  # A=添加, M=修改, D=删除, R=重命名
    diff_content: str


class GitOperator:
    """Git 操作类"""

    def __init__(self):
        self.repo_root = self._get_repo_root()

    def _get_repo_root(self) -> Optional[str]:
        """获取 Git 仓库根目录"""
        try:
            result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def is_git_repo(self) -> bool:
        """检查当前目录是否为 Git 仓库"""
        return self.repo_root is not None

    def get_staged_changes(self) -> List[GitChange]:
        """获取暂存区的所有修改"""
        if not self.is_git_repo():
            raise RuntimeError("当前目录不是一个 Git 仓库")

        changes = []

        # 获取暂存区文件状态
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-status"], capture_output=True, text=True, check=True
            )

            if not result.stdout.strip():
                return changes

            # 解析文件状态
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) >= 2:
                    change_type = parts[0]
                    file_path = parts[1]

                    # 获取具体的 diff 内容
                    diff_content = self._get_file_diff(file_path)

                    changes.append(GitChange(file_path=file_path, change_type=change_type, diff_content=diff_content))

            return changes

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"获取暂存区修改失败: {e}")

    def _get_file_diff(self, file_path: str) -> str:
        """获取文件的具体 diff 内容"""
        try:
            result = subprocess.run(["git", "diff", "--cached", file_path], capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""

    def get_commit_changes(self, commit_ref: str) -> List[GitChange]:
        """获取指定commit的所有修改"""
        if not self.is_git_repo():
            raise RuntimeError("当前目录不是一个 Git 仓库")

        changes = []

        try:
            # 获取commit的文件变更状态
            result = subprocess.run(
                ["git", "diff", "--name-status", f"{commit_ref}^", commit_ref],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                return changes

            # 解析文件状态
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) >= 2:
                    change_type = parts[0]
                    file_path = parts[1]

                    # 获取具体的 diff 内容
                    diff_content = self._get_commit_file_diff(commit_ref, file_path)

                    changes.append(GitChange(file_path=file_path, change_type=change_type, diff_content=diff_content))

            return changes

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"获取commit修改失败: {e}")

    def _get_commit_file_diff(self, commit_ref: str, file_path: str) -> str:
        """获取commit中指定文件的diff内容"""
        try:
            result = subprocess.run(
                ["git", "diff", f"{commit_ref}^", commit_ref, "--", file_path],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ""

    def get_commit_info(self, commit_ref: str) -> Dict:
        """获取commit基本信息"""
        if not self.is_git_repo():
            return {"error": "当前目录不是一个 Git 仓库"}

        try:
            # 获取commit hash
            hash_result = subprocess.run(["git", "rev-parse", commit_ref], capture_output=True, text=True, check=True)
            commit_hash = hash_result.stdout.strip()

            # 获取commit作者
            author_result = subprocess.run(
                ["git", "show", "--format=%an", "--no-patch", commit_ref], capture_output=True, text=True, check=True
            )
            author = author_result.stdout.strip()

            # 获取commit日期
            date_result = subprocess.run(
                ["git", "show", "--format=%ad", "--no-patch", commit_ref], capture_output=True, text=True, check=True
            )
            date = date_result.stdout.strip()

            # 获取完整的commit消息
            message_result = subprocess.run(
                ["git", "show", "--format=%B", "--no-patch", commit_ref], capture_output=True, text=True, check=True
            )
            message = message_result.stdout.strip()

            return {"hash": commit_hash, "author": author, "date": date, "message": message}

        except subprocess.CalledProcessError as e:
            return {"error": f"获取commit信息失败: {e}"}


class AIProvider:
    """AI 服务提供者基类"""

    def generate_commit_message(self, changes: List[GitChange], language: str = "en") -> str:
        """生成 commit message"""
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    """OpenAI API 提供者"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        # 创建 OpenAI 客户端
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate_commit_message(self, changes: List[GitChange], language: str = "en") -> str:
        """使用 OpenAI SDK 生成 commit message"""

        # 构建提示词
        prompt = self._build_prompt(changes, language)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(language),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=1.0,
                max_tokens=8192,
                stream=True,  # 使用流式响应
            )

            # 处理流式响应并实时显示
            commit_message = ""
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    print(content, end="")  # 实时显示生成内容
                    commit_message += content

            print()  # 换行，结束流式显示
            return commit_message.strip()

        except Exception as e:
            raise RuntimeError(f"调用 AI API 失败: {e}")

    def _get_system_prompt(self, language: str = "en") -> str:
        """根据语言获取系统提示词"""
        if language == "zh" or language == "zh-cn":
            return """你是一个专业的 Git Commit Message 生成助手。
请严格按照以下要求：
1. 直接返回commit message，不要任何解释、分析或额外文字
2. 使用约定式提交规范格式：<type>(<scope>): <description>
3. 返回内容必须是中文
4. 如果修改内容较少, 直接返回commit message 即可; 如果修改内容较多, 可以包含多行描述来详细说明修改内容, 但不要超过10行, 每行使用 - 开头"""
        else:
            return """You are a professional Git Commit Message generator.
Please strictly follow these requirements:
1. Return ONLY the commit message, no explanations, analysis, or additional text
2. Use conventional commit format: <type>(<scope>): <description>
3. Return content must be in English
4. If the changes are few, return the commit message directly; if the changes are many, can include multiple lines to describe changes in detail, but not more than 10 lines, each line starts with -"""

    def _build_prompt(self, changes: List[GitChange], language: str = "en") -> str:
        """构建发送给 AI 的提示词"""

        if not changes:
            if language == "zh" or language == "zh-cn":
                return "没有检测到暂存区的修改。"
            else:
                return "No staged changes detected."

        if language == "zh" or language == "zh-cn":
            prompt_lines = [
                "请基于以下 Git 暂存区的修改内容，生成一个符合约定式提交规范的 commit message：",
                "",
                "修改文件信息：",
            ]
            change_type_map = {"A": "新增", "M": "修改", "D": "删除", "R": "重命名"}
            requirements = [
                "要求：",
                "1. 使用约定式提交规范格式：<type>(<scope>): <description>",
                "2. type 可以是: feat, fix, docs, style, refactor, test, chore 等",
                "3. description 使用中文，简洁明了地描述修改内容",
                "4. 如果修改涉及多个方面，选择最主要的类型",
                "5. 只返回 commit message，不要其他任何文字",
                "",
            ]
        else:
            prompt_lines = [
                "Please generate a conventional commit message based on the following Git staged changes:",
                "",
                "Changed files:",
            ]
            change_type_map = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}
            requirements = [
                "Requirements:",
                "1. Use conventional commit format: <type>(<scope>): <description>",
                "2. type can be: feat, fix, docs, style, refactor, test, chore, etc.",
                "3. description in English, concise and clear",
                "4. If changes involve multiple aspects, choose the most important type",
                "5. Return ONLY the commit message, no other text",
                "",
            ]

        for i, change in enumerate(changes, 1):
            change_desc = change_type_map.get(change.change_type, change.change_type)
            prompt_lines.append(f"{i}. {change_desc}: {change.file_path}")

            # 添加完整的 diff 内容，不做任何限制
            if change.diff_content:
                if language == "zh" or language == "zh-cn":
                    prompt_lines.append("   修改内容：")
                else:
                    prompt_lines.append("   Changes:")
                # 将完整的 diff 内容添加到提示词中
                for line in change.diff_content.split("\n"):
                    if line.strip():  # 只过滤空行
                        prompt_lines.append(f"   {line}")

            prompt_lines.append("")

        prompt_lines.extend(requirements)

        return "\n".join(prompt_lines)


class FastCommit:
    """FastCommit 主类"""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.git_operator = GitOperator()
        self.ai_provider = ai_provider

    def set_ai_provider(self, provider: AIProvider):
        """设置 AI 提供者"""
        self.ai_provider = provider

    def check_prerequisites(self) -> Tuple[bool, str]:
        """检查运行前提条件"""

        # 检查是否在 Git 仓库中
        if not self.git_operator.is_git_repo():
            return False, "当前目录不是一个 Git 仓库"

        # 检查是否配置了 AI 提供者
        if not self.ai_provider:
            return False, "未配置 AI 提供者，请先配置 API"

        return True, "检查通过"

    def generate_commit_message(self, language: str = "en") -> str:
        """生成 commit message"""

        # 检查前提条件
        is_valid, message = self.check_prerequisites()
        if not is_valid:
            raise RuntimeError(message)

        # 获取暂存区修改
        changes = self.git_operator.get_staged_changes()

        if not changes:
            raise RuntimeError("暂存区没有修改，请先使用 'git add' 添加要提交的文件")

        # 生成 commit message
        commit_msg = self.ai_provider.generate_commit_message(changes, language)

        return commit_msg

    def get_staged_files_summary(self) -> Dict:
        """获取暂存区文件摘要信息"""

        if not self.git_operator.is_git_repo():
            return {"error": "当前目录不是一个 Git 仓库"}

        changes = self.git_operator.get_staged_changes()

        if not changes:
            return {"message": "暂存区没有修改"}

        summary = {"total_files": len(changes), "changes": []}

        for change in changes:
            change_type_map = {"A": "新增", "M": "修改", "D": "删除", "R": "重命名"}

            summary["changes"].append(
                {
                    "file": change.file_path,
                    "type": change_type_map.get(change.change_type, change.change_type),
                    "raw_type": change.change_type,
                }
            )

        return summary

    def get_commit_info(self, commit_ref: str) -> Dict:
        """获取commit信息并包含变更内容"""
        # 获取基本commit信息
        commit_info = self.git_operator.get_commit_info(commit_ref)

        if "error" in commit_info:
            return commit_info

        # 获取变更内容
        try:
            changes = self.git_operator.get_commit_changes(commit_ref)

            # 转换为显示格式
            change_type_map = {"A": "新增", "M": "修改", "D": "删除", "R": "重命名"}
            change_list = []
            for change in changes:
                change_list.append(
                    {
                        "file": change.file_path,
                        "type": change_type_map.get(change.change_type, change.change_type),
                        "raw_type": change.change_type,
                    }
                )

            commit_info["changes"] = change_list
            commit_info["change_objects"] = changes  # 保留原始对象用于AI分析

            return commit_info

        except Exception as e:
            return {"error": f"获取commit变更失败: {e}"}
