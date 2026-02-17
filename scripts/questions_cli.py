#!/usr/bin/env python3
"""
疑问系统 CLI 工具

用于记录和管理阅读论文时产生的疑问
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.questions_system import QuestionsManager, Question

try:
    from colorama import init, Fore, Style
    init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = ""
    class Style:
        RESET_ALL = BRIGHT = ""


def print_header(text: str):
    """打印标题"""
    if HAS_COLOR:
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}")
    else:
        print(f"\n{text}")
    print("─" * 60)


def print_success(text: str):
    """打印成功信息"""
    if HAS_COLOR:
        print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")
    else:
        print(f"✅ {text}")


def print_error(text: str):
    """打印错误信息"""
    if HAS_COLOR:
        print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")
    else:
        print(f"❌ {text}")


def print_warning(text: str):
    """打印警告信息"""
    if HAS_COLOR:
        print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")
    else:
        print(f"⚠️  {text}")


def print_info(text: str):
    """打印信息"""
    if HAS_COLOR:
        print(f"{Fore.BLUE}ℹ️  {text}{Style.RESET_ALL}")
    else:
        print(f"ℹ️  {text}")


def print_question(question: Question, show_answers: bool = False):
    """打印问题详情"""
    status_emoji = {
        'unsolved': '❓',
        'partial': '🤔',
        'solved': '✅'
    }

    emoji = status_emoji.get(question.status, '❓')
    importance = '⭐' * question.importance

    print(f"\n{emoji} [{question.id}] {question.content}")
    print(f"   类型: {question.question_type} | 重要性: {importance} | 状态: {question.status}")

    if question.section:
        print(f"   章节: {question.section}", end="")
        if question.page:
            print(f", 页码: {question.page}", end="")
        print()

    if question.context:
        print(f"   上下文: {question.context[:100]}...")

    if question.tags:
        print(f"   标签: {', '.join(question.tags)}")

    if show_answers and question.answers:
        print(f"   答案数: {len(question.answers)}")
        for i, ans in enumerate(question.answers, 1):
            print(f"      {i}. {ans.content[:80]}...")
            print(f"         来源: {ans.source}, 置信度: {ans.confidence}")


def cmd_start_session(args, manager: QuestionsManager):
    """开始问题记录会话"""
    print_header("📖 开始问题记录会话")

    paper_id = args.paper
    if not paper_id:
        paper_id = input("论文ID: ").strip()
        if not paper_id:
            print_error("论文ID不能为空")
            return

    session_id = manager.start_session(paper_id)

    print_success(f"问题记录会话已开始")
    print(f"   论文: {paper_id}")
    print(f"   会话ID: {session_id}")
    print()
    print_info("使用以下命令记录问题:")
    print(f"   python {Path(__file__).name} --question")


def cmd_end_session(args, manager: QuestionsManager):
    """结束当前会话"""
    if not manager.current_session:
        print_error("当前没有活动会话")
        return

    print_header("📊 结束问题记录会话")

    notes = None
    if args.notes:
        notes = args.notes
    else:
        print("是否添加会话笔记？(直接回车跳过)")
        notes_input = input("笔记: ").strip()
        if notes_input:
            notes = notes_input

    session = manager.end_session(notes)

    if session:
        print_success("会话已结束")
        print(f"   论文: {session.paper_id}")
        print(f"   时长: {_calculate_duration(session.start_time, session.end_time)}")
        print(f"   问题数: {session.questions_count}个")
        if session.sections_covered:
            print(f"   章节: {', '.join(session.sections_covered)}")


def cmd_create_question(args, manager: QuestionsManager):
    """创建问题"""
    print_header("❓ 记录新问题")

    # 论文ID
    paper_id = args.paper
    if not paper_id:
        if manager.current_session:
            paper_id = manager.current_session.paper_id
            print(f"使用当前会话的论文: {paper_id}")
        else:
            paper_id = input("论文ID: ").strip()
            if not paper_id:
                print_error("论文ID不能为空")
                return

    # 问题内容
    content = args.content
    if not content:
        content = input("问题内容: ").strip()
        if not content:
            print_error("问题内容不能为空")
            return

    # 问题类型
    print("\n问题类型:")
    for i, (key, desc) in enumerate(QuestionsManager.QUESTION_TYPES.items(), 1):
        print(f"  {i}. {key}: {desc}")

    q_type = args.type
    if not q_type:
        type_input = input(f"选择类型 (1-{len(QuestionsManager.QUESTION_TYPES)}) [1]: ").strip()
        if not type_input:
            q_type = "understanding"
        else:
            try:
                idx = int(type_input) - 1
                q_type = list(QuestionsManager.QUESTION_TYPES.keys())[idx]
            except (ValueError, IndexError):
                q_type = "understanding"

    # 重要性
    importance = args.importance
    if importance is None:
        imp_input = input("重要性 (1-5) [3]: ").strip()
        importance = int(imp_input) if imp_input else 3

    # 难度
    difficulty = args.difficulty
    if difficulty is None:
        diff_input = input("难度 (1-5) [3]: ").strip()
        difficulty = int(diff_input) if diff_input else 3

    # 章节
    section = args.section
    if not section:
        section_input = input("章节 [可选]: ").strip()
        section = section_input if section_input else None

    # 页码
    page = args.page
    if page is None:
        page_input = input("页码 [可选]: ").strip()
        page = int(page_input) if page_input else None

    # 上下文
    context = args.context
    if not context:
        context_input = input("问题上下文 [可选]: ").strip()
        context = context_input if context_input else None

    # 标签
    tags = args.tags
    if not tags:
        tags_input = input("标签 (逗号分隔) [可选]: ").strip()
        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []

    # 创建问题
    question = manager.create_question(
        content=content,
        paper_id=paper_id,
        question_type=q_type,
        section=section,
        page=page,
        context=context,
        importance=importance,
        difficulty=difficulty,
        tags=tags
    )

    print()
    print_success(f"问题已创建: {question.id}")
    print_question(question)


def cmd_add_answer(args, manager: QuestionsManager):
    """为问题添加答案"""
    print_header("💡 添加答案")

    question_id = args.question
    if not question_id:
        question_id = input("问题ID: ").strip()
        if not question_id:
            print_error("问题ID不能为空")
            return

    question = manager.get_question(question_id)
    if not question:
        print_error(f"问题 {question_id} 不存在")
        return

    print(f"\n问题: {question.content}\n")

    # 答案内容
    content = args.content
    if not content:
        content = input("答案内容: ").strip()
        if not content:
            print_error("答案内容不能为空")
            return

    # 答案来源
    source = args.source
    if not source:
        source_input = input("答案来源 (论文ID 或 'own_thinking'): ").strip()
        source = source_input if source_input else "own_thinking"

    # 如果来自论文，询问章节
    section = None
    page = None
    quote = None
    if source != "own_thinking":
        section = input("章节 [可选]: ").strip() or None
        page_input = input("页码 [可选]: ").strip()
        page = int(page_input) if page_input else None
        quote = input("相关引用 [可选]: ").strip() or None

    # 置信度
    confidence = args.confidence
    if confidence is None:
        conf_input = input("置信度 (0-1) [0.8]: ").strip()
        confidence = float(conf_input) if conf_input else 0.8

    # 添加答案
    success = manager.add_answer(
        question_id=question_id,
        content=content,
        source=source,
        section=section,
        page=page,
        quote=quote,
        confidence=confidence
    )

    if success:
        print_success("答案已添加")
        updated_question = manager.get_question(question_id)
        print(f"问题状态: {updated_question.status}")
    else:
        print_error("添加答案失败")


def cmd_list_questions(args, manager: QuestionsManager):
    """列出问题"""
    print_header("📋 问题列表")

    # 搜索条件
    questions = manager.search_questions(
        keyword=args.keyword,
        paper_id=args.paper,
        question_type=args.type,
        status=args.status,
        min_importance=args.min_importance,
        tags=args.tags
    )

    if not questions:
        print_info("没有找到符合条件的问题")
        return

    # 按状态分组
    by_status = {
        'unsolved': [],
        'partial': [],
        'solved': []
    }

    for q in questions:
        by_status[q.status].append(q)

    total = len(questions)
    print(f"共找到 {total} 个问题\n")

    # 显示未解决的
    if by_status['unsolved']:
        print(f"{Fore.RED}❓ 未解决 ({len(by_status['unsolved'])}){Style.RESET_ALL}")
        for q in by_status['unsolved']:
            print_question(q)

    # 显示部分解决的
    if by_status['partial']:
        print(f"\n{Fore.YELLOW}🤔 部分解决 ({len(by_status['partial'])}){Style.RESET_ALL}")
        for q in by_status['partial']:
            print_question(q, show_answers=True)

    # 显示已解决的
    if by_status['solved']:
        print(f"\n{Fore.GREEN}✅ 已解决 ({len(by_status['solved'])}){Style.RESET_ALL}")
        for q in by_status['solved']:
            print_question(q, show_answers=True)


def cmd_show_question(args, manager: QuestionsManager):
    """显示问题详情"""
    question_id = args.question
    if not question_id:
        print_error("请指定问题ID")
        return

    question = manager.get_question(question_id)
    if not question:
        print_error(f"问题 {question_id} 不存在")
        return

    print_header(f"问题详情: {question_id}")

    status_emoji = {
        'unsolved': '❓',
        'partial': '🤔',
        'solved': '✅'
    }

    print(f"\n{status_emoji.get(question.status, '❓')} {question.content}\n")

    print(f"论文: {question.paper_id}")
    if question.section:
        print(f"章节: {question.section}", end="")
        if question.page:
            print(f", 页码: {question.page}")
        else:
            print()

    print(f"类型: {question.question_type}")
    print(f"重要性: {'⭐' * question.importance} ({question.importance}/5)")
    print(f"难度: {'🔥' * question.difficulty} ({question.difficulty}/5)")
    print(f"状态: {question.status}")

    if question.context:
        print(f"\n上下文:")
        print(f"  {question.context}")

    if question.tags:
        print(f"\n标签: {', '.join(question.tags)}")

    if question.related_insights:
        print(f"\n相关洞察: {', '.join(question.related_insights)}")

    if question.related_questions:
        print(f"\n相关问题: {', '.join(question.related_questions)}")

    if question.answers:
        print(f"\n{'='*60}")
        print(f"答案 ({len(question.answers)}个):\n")
        for i, ans in enumerate(question.answers, 1):
            print(f"{i}. {ans.content}")
            print(f"   来源: {ans.source}")
            if ans.section:
                print(f"   章节: {ans.section}", end="")
                if ans.page:
                    print(f", 页码: {ans.page}")
                else:
                    print()
            if ans.quote:
                print(f"   引用: \"{ans.quote}\"")
            print(f"   置信度: {ans.confidence}")
            print(f"   时间: {ans.created_at[:10]}")
            print()

    if question.notes:
        print(f"备注: {question.notes}")

    print(f"\n创建时间: {question.created_at}")
    if question.resolved_at:
        print(f"解决时间: {question.resolved_at}")


def cmd_update_status(args, manager: QuestionsManager):
    """更新问题状态"""
    question_id = args.question
    status = args.status

    if not question_id or not status:
        print_error("请指定问题ID和状态")
        return

    if status not in ['unsolved', 'partial', 'solved']:
        print_error("状态必须是: unsolved, partial, solved")
        return

    success = manager.update_question_status(question_id, status)
    if success:
        print_success(f"问题 {question_id} 状态已更新为: {status}")
    else:
        print_error(f"问题 {question_id} 不存在")


def cmd_link_questions(args, manager: QuestionsManager):
    """关联问题"""
    q1 = args.question1
    q2 = args.question2

    if not q1 or not q2:
        print_error("请指定两个问题ID")
        return

    success = manager.link_questions(q1, q2)
    if success:
        print_success(f"问题 {q1} 和 {q2} 已关联")
    else:
        print_error("关联失败，请检查问题ID是否正确")


def cmd_statistics(args, manager: QuestionsManager):
    """显示统计信息"""
    print_header("📊 疑问系统统计")

    stats = manager.get_statistics()

    print(f"\n总问题数: {stats['total_questions']}")
    print(f"总会话数: {stats['total_sessions']}")
    print(f"解决率: {stats['solve_rate']:.1%}\n")

    # 按状态统计
    print("按状态分布:")
    for status, count in stats['by_status'].items():
        percentage = count / stats['total_questions'] * 100
        print(f"  {status:12s}: {count:3d} ({percentage:5.1f}%)")

    # 按类型统计
    print("\n按类型分布:")
    for q_type, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
        percentage = count / stats['total_questions'] * 100
        print(f"  {q_type:20s}: {count:3d} ({percentage:5.1f}%)")

    # 按论文统计
    print("\n按论文分布:")
    for paper_id, count in sorted(stats['by_paper'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {paper_id:20s}: {count:3d}问题")


def cmd_export(args, manager: QuestionsManager):
    """导出问题"""
    if not args.paper:
        print_error("请指定论文ID")
        return

    output_format = args.format or 'markdown'
    content = manager.export_questions_by_paper(args.paper, output_format)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(content)
        print_success(f"已导出到: {args.output}")
    else:
        print(content)


def _calculate_duration(start_time: str, end_time: Optional[str]) -> str:
    """计算时长"""
    if not end_time:
        return "进行中"

    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)
    duration = end - start

    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60

    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    else:
        return f"{minutes}分钟"


def main():
    parser = argparse.ArgumentParser(
        description="疑问系统 - 记录和管理阅读论文时产生的疑问",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 开始问题记录会话
  python questions_cli.py --start-session --paper 1810_04805

  # 记录问题
  python questions_cli.py --question

  # 添加答案
  python questions_cli.py --add-answer --question q_0001

  # 查看所有未解决的问题
  python questions_cli.py --list --status unsolved

  # 查看统计
  python questions_cli.py --stats
        """
    )

    # 会话管理
    parser.add_argument('--start-session', action='store_true',
                        help='开始问题记录会话')
    parser.add_argument('--end-session', action='store_true',
                        help='结束当前会话')

    # 问题管理
    parser.add_argument('--question', '-q', action='store_true',
                        help='记录新问题（交互式）')
    parser.add_argument('--add-answer', action='store_true',
                        help='为问题添加答案')
    parser.add_argument('--list', '-l', action='store_true',
                        help='列出问题')
    parser.add_argument('--show', action='store_true',
                        help='显示问题详情')
    parser.add_argument('--update-status', action='store_true',
                        help='更新问题状态')
    parser.add_argument('--link', action='store_true',
                        help='关联两个问题')

    # 统计和导出
    parser.add_argument('--stats', action='store_true',
                        help='显示统计信息')
    parser.add_argument('--export', action='store_true',
                        help='导出问题')

    # 参数
    parser.add_argument('--paper', type=str,
                        help='论文ID')
    parser.add_argument('--content', type=str,
                        help='问题或答案内容')
    parser.add_argument('--type', type=str,
                        help='问题类型')
    parser.add_argument('--section', type=str,
                        help='章节')
    parser.add_argument('--page', type=int,
                        help='页码')
    parser.add_argument('--context', type=str,
                        help='问题上下文')
    parser.add_argument('--importance', type=int,
                        help='重要性 (1-5)')
    parser.add_argument('--difficulty', type=int,
                        help='难度 (1-5)')
    parser.add_argument('--tags', type=str, nargs='+',
                        help='标签')
    parser.add_argument('--status', type=str,
                        help='问题状态')
    parser.add_argument('--source', type=str,
                        help='答案来源')
    parser.add_argument('--confidence', type=float,
                        help='答案置信度')
    parser.add_argument('--keyword', type=str,
                        help='搜索关键词')
    parser.add_argument('--min-importance', type=int,
                        help='最低重要性')
    parser.add_argument('--question1', type=str,
                        help='第一个问题ID')
    parser.add_argument('--question2', type=str,
                        help='第二个问题ID')
    parser.add_argument('--notes', type=str,
                        help='笔记')
    parser.add_argument('--format', type=str,
                        help='导出格式 (markdown/json)')
    parser.add_argument('--output', type=str,
                        help='输出文件')

    args = parser.parse_args()

    # 初始化管理器
    manager = QuestionsManager()

    # 执行命令
    if args.start_session:
        cmd_start_session(args, manager)
    elif args.end_session:
        cmd_end_session(args, manager)
    elif args.question:
        cmd_create_question(args, manager)
    elif args.add_answer:
        cmd_add_answer(args, manager)
    elif args.list:
        cmd_list_questions(args, manager)
    elif args.show:
        cmd_show_question(args, manager)
    elif args.update_status:
        cmd_update_status(args, manager)
    elif args.link:
        cmd_link_questions(args, manager)
    elif args.stats:
        cmd_statistics(args, manager)
    elif args.export:
        cmd_export(args, manager)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
