#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块

Copyright (c) 2024 antiproton
License: MIT
"""

import os
import re
import ssl
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime


def create_ssl_context():
    """创建 SSL 上下文，禁用证书验证（解决 Windows SSL 问题）"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def fetch_arxiv_papers(query, max_results=10, domain=None, retry_count=3, years=10):
    """
    从 arXiv 搜索论文（带重试和延时机制，默认近10年）
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数
        domain: 领域名称，用于匹配顶级期刊
        retry_count: 失败时重试次数
        years: 搜索最近多少年的论文，默认10年
        
    Returns:
        论文列表，每项为字典
    """
    import urllib.parse
    from datetime import datetime
    
    # 计算年份范围
    current_year = datetime.now().year
    start_year = current_year - years
    
    for attempt in range(retry_count):
        try:
            query_encoded = urllib.parse.quote(query)
            # 添加年份过滤：submittedDate:[YYYYMM TO YYYYMM]
            date_filter = f"submittedDate:[{start_year}01 TO {current_year}12]"
            # 组合查询：关键词 AND 日期范围（关键词加引号确保短语匹配）
            combined_query = urllib.parse.quote(f'all:"{query}" AND {date_filter}')
            url = f"http://export.arxiv.org/api/query?search_query={combined_query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
            
            req = urllib.request.Request(url, headers={
                "User-Agent": "PaperIdea/1.0 (Academic Research Tool)"
            })
            
            # 使用 SSL 上下文禁用证书验证
            ssl_context = create_ssl_context()
            
            # 增加超时时间到60秒
            with urllib.request.urlopen(req, timeout=60, context=ssl_context) as response:
                data = response.read().decode('utf-8')
            
            # 成功获取数据，解析并返回
            return _parse_arxiv_response(data, domain)
            
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # 请求过于频繁，等待后重试
                wait_time = (attempt + 1) * 2
                print(f"⚠️ arXiv 请求过于频繁 (429)，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                if attempt == retry_count - 1:
                    print(f"⚠️ arXiv 搜索失败 (429): 达到最大重试次数")
                    return []
            else:
                print(f"⚠️ arXiv 搜索失败 (HTTP {e.code}): {e}")
                return []
                
        except urllib.error.URLError as e:
            # 网络错误，可能是超时
            wait_time = (attempt + 1) * 2
            print(f"⚠️ arXiv 网络错误，等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
            if attempt == retry_count - 1:
                print(f"⚠️ arXiv 搜索失败: 网络错误，达到最大重试次数")
                return []
                
        except Exception as e:
            print(f"⚠️ arXiv 搜索失败: {str(e)[:100]}")
            return []
    
    return []


def _parse_arxiv_response(data, domain=None):
    """解析 arXiv API 响应"""
    root = ET.fromstring(data)
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
    
    # 加载顶级期刊列表
    from prompt_manager import PromptManager
    pm = PromptManager()
    top_journals = pm.load_top_journals()
    
    papers = []
    for entry in root.findall('atom:entry', ns):
        title = entry.find('atom:title', ns)
        summary = entry.find('atom:summary', ns)
        published = entry.find('atom:published', ns)
        link = entry.find('atom:id', ns)
        
        # 提取期刊信息
        journal_ref = entry.find('arxiv:journal_ref', ns)
        journal_text = journal_ref.text.strip() if journal_ref is not None else ""
        
        title_text = title.text.strip() if title is not None else "N/A"
        summary_text = summary.text.strip() if summary is not None else "N/A"
        published_text = published.text[:10] if published is not None else "N/A"
        link_text = link.text if link is not None else "N/A"
        
        # 提取年份
        year = "N/A"
        if published_text and len(published_text) >= 4:
            try:
                year = int(published_text[:4])
            except:
                pass
        
        # 获取作者
        authors = []
        for author in entry.findall('atom:author', ns):
            name = author.find('atom:name', ns)
            if name is not None:
                authors.append(name.text)
        
        # 检查是否为顶级期刊
        is_top_journal = False
        matched_journal = ""
        if journal_text and top_journals:
            journal_lower = journal_text.lower()
            for full_name, aliases in top_journals.items():
                for alias in aliases:
                    if alias.lower() in journal_lower:
                        is_top_journal = True
                        matched_journal = full_name
                        break
                if is_top_journal:
                    break
        
        paper = {
            'title': title_text.replace('\n', ' '),
            'summary': summary_text.replace('\n', ' '),
            'authors': ', '.join(authors[:3]) + (' et al.' if len(authors) > 3 else ''),
            'published': published_text,
            'year': year,
            'link': link_text,
            'journal_ref': journal_text,
            'is_top_journal': is_top_journal,
            'matched_journal': matched_journal
        }
        papers.append(paper)
    
    # 按顶刊和年份排序
    papers.sort(key=lambda x: (-x['is_top_journal'], -x['year'] if isinstance(x['year'], int) else 0))
    
    return papers


def extract_arxiv_id(arxiv_input):
    """从各种格式的 arXiv 输入中提取 ID"""
    patterns = [
        r'arxiv[:\s]+(\d{4}\.\d{4,5})',
        r'arxiv\.org/abs/(\d{4}\.\d{4,5})',
        r'^(\d{4}\.\d{4,5})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, arxiv_input, re.IGNORECASE)
        if match:
            return match.group(1)
    raise ValueError(f"无法解析 arXiv ID: {arxiv_input}")


def save_result(command, topic, content, output_dir=None):
    """保存结果到文件"""
    if output_dir is None:
        output_dir = Path("outputs")
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    safe_topic = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in topic[:50])
    timestamp = datetime.now().strftime('%m%d_%H%M')
    filename = f"{command}_{safe_topic}_{timestamp}.md"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {command}: {topic}\n\n")
        f.write(f"Generated by PaperIdea\n")
        f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write(content)
    
    return filepath


def open_file(filepath):
    """用系统默认程序打开文件"""
    import platform
    import subprocess
    
    system = platform.system()
    filepath = str(filepath)
    
    try:
        if system == 'Windows':
            os.startfile(filepath)
        elif system == 'Darwin':
            subprocess.run(['open', filepath], check=True)
        else:
            subprocess.run(['xdg-open', filepath], check=True)
    except Exception as e:
        print(f"⚠️ 无法自动打开文件: {e}")


def format_related_work_markdown(research_results):
    """将调研结果格式化为 Markdown 表格（模型中心化结构）"""
    md = ""
    has_top_journals = False
    
    # 1. 模型相关论文（arXiv搜索的唯一来源）
    model_papers = research_results.get("model_related", [])
    if model_papers:
        md += "\n### 📚 相关模型论文（基于语义扩展）\n\n"
        md += "| 论文 | 年份 | 来源 | 链接 |\n"
        md += "|------|------|------|------|\n"
        for p in model_papers[:6]:
            title = p['title'][:50] + "..." if len(p['title']) > 50 else p['title']
            if p.get('is_top_journal'):
                source = f"⭐{p.get('matched_journal', '顶刊')}"
                has_top_journals = True
            elif p.get('journal_ref'):
                source = p['journal_ref'][:20] + "..." if len(p['journal_ref']) > 20 else p['journal_ref']
            else:
                source = "arXiv"
            md += f"| {title} | {p['published']} | {source} | [链接]({p['link']}) |\n"
    
    # 2. AI推断的方法迁移建议（不基于arXiv搜索）
    method_suggestions = research_results.get("method_suggestions", {})
    if method_suggestions:
        md += "\n### 💡 AI推断的方法迁移建议\n\n"
        
        # Type B1: 同模型替代方法（"同大类不同小类"的算法替换）
        b1_suggestions = method_suggestions.get("type_b1_same_model_alternatives", [])
        if b1_suggestions:
            md += "\n**Type B1 - 同模型替代方法（算法替换）**:\n\n"
            for sugg in b1_suggestions[:3]:
                model = sugg.get('model', 'N/A')
                current = sugg.get('current_method', 'N/A')
                suggested = sugg.get('suggested_method', 'N/A')
                reasoning = sugg.get('reasoning', '')
                md += f"- **{model}**: 「{suggested}」→ 替代 → 「{current}」\n"
                if reasoning:
                    md += f"  - 依据: {reasoning[:120]}...\n"
                md += "\n"
        
        # Type B2: 同方法，新模型
        b2_suggestions = method_suggestions.get("type_b2_same_method_new_models", [])
        if b2_suggestions:
            md += "\n**Type B2 - 同方法新模型**:\n\n"
            for sugg in b2_suggestions[:3]:
                method = sugg.get('method', 'N/A')
                new_model = sugg.get('suggested_model', 'N/A')
                isomorphism = sugg.get('isomorphism', '')
                md += f"- **{method}** → 应用于 → **{new_model}**\n"
                if isomorphism:
                    md += f"  - 数学同构性: {isomorphism[:120]}...\n"
                md += "\n"
    
    if not md:
        md = "\n未找到显著相关的工作。\n"
    
    if has_top_journals:
        md = "\n> ⭐ 标记的论文发表于该领域顶级期刊\n" + md
    
    return md
