#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论文分析核心模块
基于论文提取信息并生成延伸研究 Idea

Copyright (c) 2024 antiproton
License: MIT
"""

import json
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

from api_client import DeepSeekClient
from utils import fetch_arxiv_papers, extract_arxiv_id, create_ssl_context
from prompt_manager import PromptManager


@dataclass
class PaperInfo:
    """论文信息数据结构"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    problem: str = ""           # 核心问题
    method: str = ""            # 方法概述
    models: List[str] = field(default_factory=list)      # 研究模型
    algorithms: List[str] = field(default_factory=list)  # 使用算法
    datasets: List[str] = field(default_factory=list)    # 数据集
    contributions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    future_work: List[str] = field(default_factory=list)
    key_citations: List[str] = field(default_factory=list)
    source: str = ""            # 'pdf' 或 'arxiv'
    arxiv_id: str = ""
    pdf_path: str = ""


class PaperAnalyzer:
    """论文分析器"""
    
    def __init__(self, client: Optional[DeepSeekClient] = None):
        """
        初始化分析器
        
        Args:
            client: DeepSeek API 客户端，如果为 None 则创建新实例
        """
        self.client = client or DeepSeekClient()
        self.prompt_manager = PromptManager()
    
    def parse_paper(self, paper_input: str, status_callback: Optional[Callable] = None) -> PaperInfo:
        """
        解析论文，提取关键信息
        
        Args:
            paper_input: PDF 路径或 arXiv ID/链接
            status_callback: 状态回调函数，用于更新进度
            
        Returns:
            PaperInfo 对象
        """
        if status_callback:
            status_callback("正在识别输入类型...")
        
        paper = PaperInfo()
        
        # 判断输入类型
        if paper_input.lower().endswith('.pdf'):
            # PDF 文件
            paper.source = 'pdf'
            paper.pdf_path = paper_input
            text_content = self._extract_pdf_text(paper_input, status_callback)
        elif 'arxiv' in paper_input.lower() or re.match(r'^\d{4}\.\d{4,5}$', paper_input):
            # arXiv ID 或链接
            paper.source = 'arxiv'
            arxiv_id = extract_arxiv_id(paper_input)
            paper.arxiv_id = arxiv_id
            
            if status_callback:
                status_callback("正在获取 arXiv 内容...")
                
            text_content = self._fetch_arxiv_content(arxiv_id)
            arxiv_meta = self._fetch_arxiv_metadata(arxiv_id)
            if arxiv_meta:
                paper.title = arxiv_meta.get('title', '')
                paper.authors = arxiv_meta.get('authors', '').split(', ') if arxiv_meta.get('authors') else []
                paper.abstract = arxiv_meta.get('summary', '')
        else:
            raise ValueError("不支持的输入格式。请提供 PDF 文件路径或 arXiv ID/链接")
        
        if not text_content or len(text_content) < 100:
            raise ValueError("无法提取论文内容，请检查文件或链接是否有效")
        
        # 使用 LLM 提取结构化信息
        if status_callback:
            status_callback("正在使用 AI 分析论文结构...")
            
        structured_info = self._extract_paper_structure(text_content, paper.abstract)
        
        # 更新论文信息
        if not paper.title:
            paper.title = structured_info.get('title', 'Unknown')
        if not paper.abstract:
            paper.abstract = structured_info.get('abstract', '')
        paper.problem = structured_info.get('problem', '')
        paper.method = structured_info.get('method', '')
        paper.models = structured_info.get('models', [])
        paper.algorithms = structured_info.get('algorithms', [])
        paper.datasets = structured_info.get('datasets', [])
        paper.contributions = structured_info.get('contributions', [])
        paper.limitations = structured_info.get('limitations', [])
        paper.future_work = structured_info.get('future_work', [])
        paper.key_citations = structured_info.get('key_citations', [])
        
        return paper
    
    def _extract_pdf_text(self, pdf_path: str, status_callback: Optional[Callable] = None) -> str:
        """从 PDF 提取文本"""
        try:
            from pypdf import PdfReader
            
            if status_callback:
                status_callback("正在读取 PDF 文件...")
                
            with open(pdf_path, 'rb') as f:
                pdf_reader = PdfReader(f)
                text = ""
                # 只读取前 10 页（通常包含关键信息）
                total_pages = min(10, len(pdf_reader.pages))
                for i, page in enumerate(pdf_reader.pages[:total_pages]):
                    if status_callback and i % 3 == 0:
                        status_callback(f"正在解析 PDF 第 {i+1}/{total_pages} 页...")
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            raise ValueError("PDF 解析需要 pypdf。请运行: pip install pypdf")
        except Exception as e:
            raise ValueError(f"PDF 解析失败: {e}")
    
    def _fetch_arxiv_content(self, arxiv_id: str) -> str:
        """获取 arXiv 论文内容（摘要）"""
        try:
            url = f"http://export.arxiv.org/api/query?search_query=id:{arxiv_id}&start=0&max_results=1"
            ssl_context = create_ssl_context()
            response = urllib.request.urlopen(url, timeout=30, context=ssl_context)
            data = response.read().decode('utf-8')
            
            root = ET.fromstring(data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            entry = root.find('atom:entry', ns)
            if entry is not None:
                summary = entry.find('atom:summary', ns)
                if summary is not None:
                    return summary.text.strip()
            return ""
        except Exception as e:
            print(f"⚠️ 获取 arXiv 内容失败: {e}")
            return ""
    
    def _fetch_arxiv_metadata(self, arxiv_id: str) -> Optional[Dict]:
        """获取 arXiv 元数据"""
        try:
            url = f"http://export.arxiv.org/api/query?search_query=id:{arxiv_id}&start=0&max_results=1"
            ssl_context = create_ssl_context()
            response = urllib.request.urlopen(url, timeout=30, context=ssl_context)
            data = response.read().decode('utf-8')
            
            root = ET.fromstring(data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            entry = root.find('atom:entry', ns)
            if entry is not None:
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text)
                
                return {
                    'title': title.text.strip() if title is not None else '',
                    'summary': summary.text.strip() if summary is not None else '',
                    'authors': ', '.join(authors)
                }
            return None
        except Exception as e:
            print(f"⚠️ 获取 arXiv 元数据失败: {e}")
            return None
    
    def _extract_paper_structure(self, text: str, abstract: str = "") -> Dict:
        """使用 LLM 提取论文结构"""
        # 截取前 8000 字符（通常是标题、摘要、引言）
        text_sample = text[:8000]
        
        # 使用 PromptManager 获取 messages
        messages = self.prompt_manager.get_messages(
            task="extract_structure",
            variables={
                "text_sample": text_sample,
                "abstract": abstract
            }
        )
        
        result = self.client.chat(messages, temperature=0.3, max_tokens=2000)
        
        # 解析 JSON
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            # 如果都失败，返回空结构
            print("⚠️ JSON 解析失败，使用默认结构")
            return {
                "title": "",
                "abstract": abstract,
                "problem": "",
                "method": "",
                "models": [],
                "algorithms": [],
                "datasets": [],
                "contributions": [],
                "limitations": [],
                "future_work": [],
                "key_citations": []
            }
    
    def _expand_model_semantically(self, models: List[str]) -> Dict[str, List[str]]:
        """
        使用AI对模型名称进行语义扩展
        
        Args:
            models: 原始模型名称列表
            
        Returns:
            包含扩展结果的字典
        """
        if not models:
            return {"original": [], "similar_models": [], "broader_concepts": [], "related_methods": []}
        
        try:
            messages = self.prompt_manager.get_messages(
                task="expand_model",
                variables={"models": models}
            )
            
            result = self.client.chat(messages, temperature=0.3, max_tokens=1000)
            
            # 解析JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # 尝试从文本中提取JSON
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ 模型语义扩展失败: {e}")
        
        # 失败时返回原始模型
        return {
            "original": models,
            "similar_models": [],
            "broader_concepts": [],
            "related_methods": []
        }
    
    def _infer_method_suggestions(self, paper: PaperInfo) -> Dict:
        """
        使用AI推断方法迁移建议（替代原有的arXiv搜索）
        
        Args:
            paper: 论文信息
            
        Returns:
            包含Type B1和B2建议的字典
        """
        try:
            messages = self.prompt_manager.get_messages(
                task="infer_methods",
                variables={
                    "models": paper.models,
                    "algorithms": paper.algorithms,
                    "problem": paper.problem,
                    "method": paper.method
                }
            )
            
            result = self.client.chat(messages, temperature=0.4, max_tokens=2000)
            
            # 解析JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # 尝试从文本中提取JSON
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ 方法推断失败: {e}")
        
        # 失败时返回空结构
        return {
            "type_b1_same_model_alternatives": [],
            "type_b2_same_method_new_models": []
        }
    
    def _filter_papers_by_relevance(self, papers: List[Dict], paper: PaperInfo, 
                                     status_callback: Optional[Callable] = None) -> List[Dict]:
        """
        第1轮AI调用：基于摘要筛选相关论文
        
        Args:
            papers: 搜索到的论文列表
            paper: 原始论文信息
            status_callback: 状态回调
            
        Returns:
            筛选后的论文列表（评分≥4的）
        """
        if not papers:
            return []
        
        if status_callback:
            status_callback(f"AI筛选相关论文（{len(papers)}篇）...")
        
        try:
            # 限制分析数量，避免token超限（最多12篇）
            papers_to_analyze = papers[:12]
            
            messages = self.prompt_manager.get_messages(
                task="filter_relevance",
                variables={
                    "models": paper.models,
                    "problem": paper.problem,
                    "papers": papers_to_analyze
                }
            )
            
            result = self.client.chat(messages, temperature=0.3, max_tokens=2000)
            
            # 解析JSON
            try:
                evaluation_result = json.loads(result)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    try:
                        evaluation_result = json.loads(json_match.group())
                    except:
                        print("⚠️ 相关性筛选JSON解析失败，保留所有论文")
                        return papers
                else:
                    print("⚠️ 相关性筛选无有效JSON，保留所有论文")
                    return papers
            
            # 根据评分筛选论文
            evaluations = evaluation_result.get("evaluations", [])
            filtered_papers = []
            
            for eval_item in evaluations:
                idx = eval_item.get("paper_index", 0) - 1  # JSON是1-based
                score = eval_item.get("relevance_score", 0)
                
                if 0 <= idx < len(papers_to_analyze) and score >= 4:
                    # 保留评分≥4的论文，并添加评分信息
                    paper_copy = papers_to_analyze[idx].copy()
                    paper_copy["relevance_score"] = score
                    paper_copy["relevance_reasoning"] = eval_item.get("reasoning", "")
                    filtered_papers.append(paper_copy)
            
            if status_callback:
                status_callback(f"筛选完成，保留 {len(filtered_papers)}/{len(papers)} 篇相关论文")
            
            return filtered_papers if filtered_papers else papers[:6]  # 如果全部过滤，保留前6篇
            
        except Exception as e:
            print(f"⚠️ 相关性筛选失败: {e}")
            return papers[:8]  # 失败时返回前8篇
    
    def _analyze_papers_in_detail(self, papers: List[Dict], paper: PaperInfo,
                                   status_callback: Optional[Callable] = None) -> List[Dict]:
        """
        第2轮AI调用：深度分析相关论文的方法和内容
        
        Args:
            papers: 筛选后的相关论文列表
            paper: 原始论文信息
            status_callback: 状态回调
            
        Returns:
            添加详细分析信息的论文列表
        """
        if not papers:
            return []
        
        if status_callback:
            status_callback(f"AI深度分析论文（{len(papers)}篇）...")
        
        try:
            # 限制分析数量，避免token超限（最多6篇）
            papers_to_analyze = papers[:6]
            
            messages = self.prompt_manager.get_messages(
                task="analyze_papers",
                variables={
                    "models": paper.models,
                    "algorithms": paper.algorithms,
                    "problem": paper.problem,
                    "papers": papers_to_analyze
                }
            )
            
            result = self.client.chat(messages, temperature=0.4, max_tokens=3000)
            
            # 解析JSON
            try:
                analysis_result = json.loads(result)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    try:
                        analysis_result = json.loads(json_match.group())
                    except:
                        print("⚠️ 深度分析JSON解析失败")
                        return papers_to_analyze
                else:
                    print("⚠️ 深度分析无有效JSON")
                    return papers_to_analyze
            
            # 合并分析结果到论文信息
            analyzed_papers = analysis_result.get("analyzed_papers", [])
            merged_papers = []
            
            for analysis in analyzed_papers:
                idx = analysis.get("paper_index", 0) - 1
                if 0 <= idx < len(papers_to_analyze):
                    # 合并原始信息和分析结果
                    merged = papers_to_analyze[idx].copy()
                    merged["analyzed_model"] = analysis.get("analyzed_model", "")
                    merged["method_used"] = analysis.get("method_used", "")
                    merged["key_finding"] = analysis.get("key_finding", "")
                    merged["relevance_level"] = analysis.get("relevance_to_original", "中")
                    merged["relevance_analysis"] = analysis.get("relevance_reasoning", "")
                    merged["method_transfer_opportunity"] = analysis.get("method_transfer_opportunity", "")
                    merged_papers.append(merged)
            
            return merged_papers if merged_papers else papers_to_analyze
            
        except Exception as e:
            print(f"⚠️ 深度分析失败: {e}")
            return papers[:6]
    
    def targeted_research(self, paper: PaperInfo, status_callback: Optional[Callable] = None) -> Dict:
        """
        基于论文信息进行模型中心化的精准文献调研
        仅搜索模型相关（原始模型、相似模型、更广概念），算法和结论信息仅用于AI推断
        """
        research_results = {
            "model_related": [],           # 语义扩展后的模型相关论文（唯一arXiv搜索来源）
            "method_suggestions": {},       # AI推断的方法迁移建议（B1同模型替代方法、B2同方法新模型）
            "search_terms": [],            # 用于调试的arXiv搜索关键词
            "model_expansion": {}          # 用于调试的语义扩展结果
        }
        
        # Step 1: 语义扩展模型
        if status_callback:
            status_callback("分析模型语义关联...")
        
        model_expansion = {"original": paper.models if paper.models else []}
        if paper.models:
            model_expansion = self._expand_model_semantically(paper.models)
        
        # 保存语义扩展结果用于调试
        research_results["model_expansion"] = model_expansion
        
        # Step 2: 搜索模型相关论文（基于语义扩展）
        # 仅搜索：原始模型 + 相似模型 + 更广概念
        if status_callback:
            status_callback("搜索相关模型论文...")
        
        # 构建搜索查询：原始模型 + 相似模型 + 更广概念
        search_terms = []
        search_terms.extend(model_expansion.get("original", []))
        search_terms.extend(model_expansion.get("similar_models", [])[:3])  # 取前3个相似模型
        search_terms.extend(model_expansion.get("broader_concepts", [])[:2])  # 取前2个更广概念
        
        # 保存搜索词用于调试
        research_results["search_terms"] = search_terms[:4]  # 最多4个
        
        if search_terms:
            # 分批搜索，避免查询过长
            for term in search_terms[:4]:  # 最多搜索4个扩展项
                papers = fetch_arxiv_papers(term, max_results=4)
                research_results["model_related"].extend(papers)
        
        # Step 2.5: 去重并排序搜索结果
        if research_results["model_related"]:
            # 去重：按 arXiv ID（link）去重
            seen_ids = set()
            unique_papers = []
            for p in research_results["model_related"]:
                # 从 link 提取 arXiv ID
                arxiv_id = p.get('link', '').split('/')[-1]
                if arxiv_id and arxiv_id not in seen_ids:
                    seen_ids.add(arxiv_id)
                    unique_papers.append(p)
            
            # 排序：顶刊优先，然后按年份降序（最新的在前）
            unique_papers.sort(key=lambda x: (
                -x.get('is_top_journal', False),  # 顶刊排前面（True > False）
                -x.get('year', 0) if isinstance(x.get('year'), int) else 0  # 新年份排前面
            ))
            
            research_results["model_related"] = unique_papers
        
        # Step 2.6: 第1轮AI调用 - 基于摘要筛选相关论文
        if research_results["model_related"]:
            research_results["model_related"] = self._filter_papers_by_relevance(
                research_results["model_related"], paper, status_callback
            )
        
        # Step 2.7: 第2轮AI调用 - 深度分析相关论文
        if research_results["model_related"]:
            research_results["model_related"] = self._analyze_papers_in_detail(
                research_results["model_related"], paper, status_callback
            )
        
        # Step 3: AI推断方法迁移建议（Type B1/B2）
        # 利用本论文的算法、结论、不足等信息，通过AI推断"同大类不同小类"的算法替换机会
        # 不通过arXiv搜索，完全由AI基于数学/结构同构性分析
        if status_callback:
            status_callback("AI分析方法迁移机会...")
        
        research_results["method_suggestions"] = self._infer_method_suggestions(paper)
        
        # 注意：本论文的算法、局限性、未来工作等信息仅用于AI推断方法建议和生成Idea时评估可行性
        # 不直接用于arXiv搜索
        
        return research_results
    
    def generate_extension_ideas(self, paper: PaperInfo, research_results: Dict, 
                                  status_callback: Optional[Callable] = None) -> str:
        """基于论文和调研结果生成延伸 Idea"""
        
        if status_callback:
            status_callback("分析模型和算法组合...")
        
        # 提取方法建议用于单独传递给提示模板
        method_suggestions = research_results.get("method_suggestions", {})
        
        # 提取深度分析的论文信息
        analyzed_papers = research_results.get("model_related", [])
        
        if status_callback:
            status_callback("生成直接改进类 Idea...")
        
        # 使用 PromptManager 获取 messages
        messages = self.prompt_manager.get_messages(
            task="generate_ideas",
            variables={
                "title": paper.title,
                "problem": paper.problem,
                "method": paper.method,
                "models": paper.models,
                "algorithms": paper.algorithms,
                "datasets": paper.datasets,
                "contributions": paper.contributions,
                "limitations": paper.limitations,
                "future_work": paper.future_work,
                "related_papers": self._format_research_results(research_results),
                "method_suggestions": method_suggestions,
                "analyzed_papers": analyzed_papers
            }
        )
        
        if status_callback:
            status_callback("生成方法迁移类 Idea...")
        
        ideas = self.client.chat(messages, temperature=0.7, max_tokens=3000)
        return ideas
    
    def _format_research_results(self, research_results: Dict) -> str:
        """格式化调研结果为文本摘要（模型中心化结构）"""
        related_papers_summary = ""
        
        # 1. 模型相关论文（arXiv搜索的唯一来源）
        model_papers = research_results.get("model_related", [])
        if model_papers:
            related_papers_summary += "\n📚 相关模型论文（基于语义扩展的模型搜索）:\n"
            for p in model_papers[:6]:
                top_marker = ""
                if p.get('is_top_journal'):
                    journal_name = p.get('matched_journal', '顶刊')
                    top_marker = f" [⭐顶刊:{journal_name}]"
                related_papers_summary += f"- {p['title']} ({p['published']}){top_marker}\n"
        
        # 2. AI推断的方法迁移建议（不基于arXiv搜索，基于数学同构性分析）
        method_suggestions = research_results.get("method_suggestions", {})
        if method_suggestions:
            related_papers_summary += "\n💡 AI推断的方法迁移建议（基于算法/模型的数学同构性）:\n"
            
            # Type B1: 同模型替代方法（"同大类不同小类"的算法替换）
            b1_suggestions = method_suggestions.get("type_b1_same_model_alternatives", [])
            if b1_suggestions:
                related_papers_summary += "\n【Type B1: 同模型，替代方法（算法替换）】\n"
                for sugg in b1_suggestions[:3]:
                    model = sugg.get('model', 'N/A')
                    current = sugg.get('current_method', 'N/A')
                    suggested = sugg.get('suggested_method', 'N/A')
                    reasoning = sugg.get('reasoning', '')
                    related_papers_summary += f"- 模型「{model}」: 用「{suggested}」替代「{current}」\n"
                    if reasoning:
                        related_papers_summary += f"  依据: {reasoning[:100]}...\n"
            
            # Type B2: 同方法，新模型
            b2_suggestions = method_suggestions.get("type_b2_same_method_new_models", [])
            if b2_suggestions:
                related_papers_summary += "\n【Type B2: 同方法，新模型】\n"
                for sugg in b2_suggestions[:3]:
                    method = sugg.get('method', 'N/A')
                    new_model = sugg.get('suggested_model', 'N/A')
                    isomorphism = sugg.get('isomorphism', '')
                    related_papers_summary += f"- 方法「{method}」→ 模型「{new_model}」\n"
                    if isomorphism:
                        related_papers_summary += f"  同构性: {isomorphism[:100]}...\n"
        
        return related_papers_summary if related_papers_summary else "暂无相关论文"
    
    def generate_report(self, paper: PaperInfo, research_results: Dict, ideas: str) -> str:
        """生成基于论文的分析报告"""
        from utils import format_related_work_markdown
        from datetime import datetime
        
        related_work_md = format_related_work_markdown(research_results)
        
        # 构建模型-算法组合信息
        model_algo_section = ""
        if paper.models:
            model_algo_section += f"\n**研究模型**: {', '.join(paper.models)}\n"
        if paper.algorithms:
            model_algo_section += f"\n**使用算法**: {', '.join(paper.algorithms)}\n"
        if paper.datasets:
            model_algo_section += f"\n**使用数据集**: {', '.join(paper.datasets)}\n"
        
        report = f"""# 基于论文的 Idea 发现报告

## 原始论文分析

**标题**: {paper.title}

**作者**: {', '.join(paper.authors) if paper.authors else 'N/A'}

**来源**: {'arXiv:' + paper.arxiv_id if paper.source == 'arxiv' else 'PDF'}

### 核心问题
{paper.problem if paper.problem else '未明确提取'}

### 方法概述
{paper.method if paper.method else '未明确提取'}
{model_algo_section}

### 主要贡献
{chr(10).join(['1. ' + c for c in paper.contributions]) if paper.contributions else '未明确提取'}

### 局限性
{chr(10).join(['- ' + l for l in paper.limitations]) if paper.limitations else '- 未明确提及'}

### 作者指出的未来工作
{chr(10).join(['- ' + f for f in paper.future_work]) if paper.future_work else '- 未明确提及'}

---

## 相关工作调研
{related_work_md}

---

## 推荐的延伸 Idea

{ideas}

---

## 总结与建议

基于对论文《{paper.title}》的分析，我们：
1. 提取了论文的核心问题、方法、模型、算法和局限性
2. 搜索了相关的改进工作、未来工作尝试**以及方法迁移机会**
3. 生成了从该论文出发的延伸 Idea，特别关注**相似方法+不同模型**的组合

### 💡 特别推荐
**Type B1（同模型相似方法）** 和 **Type B2（相似方法不同模型）** 类型的 Idea 最容易发表：
- B1: 在同一模型上对比不同相似方法的效果差异
- B2: 将本文算法应用到其他相似模型上
- 实验成本相对较低，结果无论正负都有价值

**建议下一步**:
- 优先查看 Type B1 和 Type B2 类型的 Idea
- Type A 需要谨慎评估，确保不是原作者故意留下的"硬骨头"
- 检查目标模型是否已有类似方法应用
- 选择可行性和创新性平衡的 Idea 深入研究

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        return report
    
    def analyze(self, paper_input: str, status_callback: Optional[Callable] = None):
        """
        完整的论文分析流程
        
        Args:
            paper_input: PDF 路径或 arXiv ID/链接
            status_callback: 状态回调函数
            
        Returns:
            tuple: (report, paper_title, search_info)
                - report: 生成的报告文本
                - paper_title: 论文标题
                - search_info: dict 包含搜索词和语义扩展结果，用于调试
        """
        # Step 1: 解析论文
        if status_callback:
            status_callback("Step 1/6: 提取论文文本...")
        paper = self.parse_paper(paper_input, status_callback)
        
        # Step 2: 精准文献调研
        if status_callback:
            status_callback("Step 2/6: 基于论文关键信息搜索相关工作...")
        research_results = self.targeted_research(paper, status_callback)
        
        # Step 3: 生成延伸 Idea
        if status_callback:
            status_callback("Step 3/6: 分析模型-算法组合...")
        ideas = self.generate_extension_ideas(paper, research_results, status_callback)
        
        # Step 4: 生成报告
        if status_callback:
            status_callback("Step 4/6: 生成结构化报告...")
        report = self.generate_report(paper, research_results, ideas)
        
        if status_callback:
            status_callback("Step 5/6: 保存报告...")
        
        # 构建调试信息
        search_info = {
            "search_terms": research_results.get("search_terms", []),
            "model_expansion": research_results.get("model_expansion", {})
        }
        
        return report, paper.title, search_info
