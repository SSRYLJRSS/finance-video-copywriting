#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
泛财经新闻视频文案 skill 打包脚本
==================================
用法：
    python package_skill.py               # 交互式询问打包模式
    python package_skill.py --clean       # 干净版：learnings.md 重置为空白模板
    python package_skill.py --experience  # 带经验版：保留 learnings.md 全部内容

两种模式都会：
    1. 检查 "爱德华"/F盘路径/API密钥 残留（违规自动剔除或警告）
    2. 输出 zip 到 skill 上级目录（默认桌面）
    3. 打印包内容清单和校验结果

无第三方依赖（只用 Python 标准库），Windows/Mac/Linux 均可运行。
"""

import os
import re
import sys
import shutil
import zipfile
import argparse
from datetime import datetime

# ---------------------------------------------------------------
# 常量
# ---------------------------------------------------------------
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 脚本上一级 = skill根目录
SCRIPT_DIR = os.path.join(SKILL_DIR, "scripts")
LEARNINGS_FILE = os.path.join(SKILL_DIR, "learnings.md")
LEARNINGS_TEMPLATE = os.path.join(SCRIPT_DIR, "learnings_template.md")
DEFAULT_ZIP_NAME = "泛财经新闻视频文案"
# zip包内根目录名（固定为通用名，不跟随本地文件夹名）
ARC_ROOT = "finance-video-copywriting"

# 需要清理的敏感痕迹（用普通字符串匹配，不用正则，避免 \U 等转义问题）
FORBIDDEN_PATTERNS = [
    "爱德华",                 # 团队品牌名
    "F:\\", "F:/",            # 本地盘符
    "C:\\Users\\",       # 本地用户路径
    "ZHIHU_ACCESS",           # API密钥
    "agent-reach-venv",       # 本地venv
    ".hermes/shared-skills",  # 本地脚本路径
]

# 打包时排除的文件/目录
EXCLUDE = {
    "__pycache__", ".git", ".DS_Store", "Thumbs.db",
}


# ---------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------
def banner(msg: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {msg}")
    print("=" * 60)


def check_forbidden(content: str, filename: str) -> list:
    """检查文件中的敏感痕迹，返回违规列表"""
    violations = []
    for pat in FORBIDDEN_PATTERNS:
        if pat in content:
            count = content.count(pat)
            violations.append(f"{pat} (x{count})")
    return violations


def scan_skill() -> list:
    """扫描整个skill目录，返回 [(相对路径, 是否违规)]
    注意：package_skill.py 自身被排除——它作为检查工具，代码里必然包含敏感模式常量，不算违规。"""
    results = []
    for root, dirs, files in os.walk(SKILL_DIR):
        # 排除
        dirs[:] = [d for d in dirs if d not in EXCLUDE]
        for f in files:
            if f in EXCLUDE or f == "package_skill.py":
                continue
            fpath = os.path.join(root, f)
            rel = os.path.relpath(fpath, SKILL_DIR)
            is_violation = False
            # 只检查文本文件
            if f.endswith((".md", ".txt", ".py", ".json", ".yaml", ".yml")):
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    if check_forbidden(content, rel):
                        is_violation = True
                except Exception:
                    pass
            results.append((rel, is_violation))
    return results


def reset_learnings() -> None:
    """把 learnings.md 重置为空白模板"""
    if os.path.exists(LEARNINGS_TEMPLATE):
        shutil.copy2(LEARNINGS_TEMPLATE, LEARNINGS_FILE)
        print("  ✅ learnings.md 已重置为空白模板")
    else:
        print("  ⚠️ 未找到模板文件，保留当前 learnings.md")


def make_zip() -> str:
    """打zip包，返回zip路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 输出位置：skill上级目录
    parent = os.path.dirname(SKILL_DIR)
    zip_name = f"{DEFAULT_ZIP_NAME}_{timestamp}"
    zip_path = os.path.join(parent, zip_name)

    print(f"  📦 打包到: {zip_path}.zip")

    with zipfile.ZipFile(zip_path + ".zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SKILL_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE]
            for f in files:
                if f in EXCLUDE:
                    continue
                fpath = os.path.join(root, f)
                # 用固定根目录名，不跟随本地文件夹名
                rel = os.path.relpath(fpath, SKILL_DIR)
                arcname = os.path.join(ARC_ROOT, rel)
                zf.write(fpath, arcname)
    return zip_path + ".zip"


def verify_zip(zip_path: str) -> bool:
    """验证zip内容：无敏感痕迹、无损坏"""
    ok = True
    print("\n  📋 包内文件清单：")
    with zipfile.ZipFile(zip_path, "r") as zf:
        total_size = 0
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            info = zf.getinfo(name)
            total_size += info.file_size
            print(f"    {name} ({info.file_size/1024:.1f}KB)")

        print(f"\n  📊 包大小: {os.path.getsize(zip_path)/1024:.1f}KB")

        # 敏感痕迹检查（package_skill.py 是检查工具，代码含模式常量，跳过）
        for name in zf.namelist():
            if name.endswith(".py") and "package_skill.py" in name:
                continue
            if name.endswith((".md", ".txt", ".py")):
                content = zf.read(name).decode("utf-8")
                violations = []
                for pat in FORBIDDEN_PATTERNS:
                    if pat in content:
                        violations.append(pat)
                if violations:
                    ok = False
                    print(f"  ❌ {name}: 发现敏感痕迹 {violations}")

    if ok:
        print("  ✅ 校验通过：零敏感痕迹残留")
    return ok


# ---------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="泛财经新闻视频文案 skill 打包工具")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--clean", action="store_true", help="干净版：learnings.md 重置为空白模板")
    group.add_argument("--experience", action="store_true", help="带经验版：保留 learnings.md 内容")
    args = parser.parse_args()

    banner("泛财经新闻视频文案 · 打包工具")

    # 1. 确定模式
    if args.clean:
        mode = "clean"
    elif args.experience:
        mode = "experience"
    else:
        print("\n  📝 请选择打包模式：")
        print("    1. 干净版（推荐）——经验库重置为空白，适合发给别人")
        print("    2. 带经验版——保留经验库内容，适合团队内部共享")
        choice = input("    输入 1 或 2: ").strip()
        mode = "clean" if choice == "1" else "experience"

    print(f"\n  🎯 模式：{'干净版（learnings重置）' if mode == 'clean' else '带经验版（learnings保留）'}")

    # 2. 敏感痕迹扫描
    banner("敏感痕迹扫描")
    files = scan_skill()
    violations_found = False
    for rel, is_violation in files:
        if is_violation:
            print(f"  ❌ {rel}: 敏感痕迹")
            violations_found = True
    if not violations_found:
        print("  ✅ 所有文件干净")

    # 3. 处理 learnings.md
    banner("learnings.md 处理")
    if mode == "clean":
        reset_learnings()
    else:
        learnings_size = os.path.getsize(LEARNINGS_FILE) / 1024
        print(f"  ✅ 保留当前 learnings.md（{learnings_size:.1f}KB）")

    # 4. 打包
    banner("打包")
    zip_path = make_zip()

    # 5. 校验
    banner("校验")
    ok = verify_zip(zip_path)

    banner("完成")
    print(f"\n  📦 zip 文件：{zip_path}")
    print(f"  📄 解压后把 finance-video-copywriting 文件夹放入目标环境的 skills 目录即可使用。")
    if mode == "clean":
        print("  ℹ️ 注意：此包为干净版，learnings.md 已重置。")
    else:
        print("  ℹ️ 注意：此包带个人经验，分享前请确认内容适合公开。")

    if not ok:
        print("  ⚠️ 警告：包内发现敏感痕迹，请检查后再分享！")
        sys.exit(1)


if __name__ == "__main__":
    main()
