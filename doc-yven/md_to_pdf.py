#!/usr/bin/env python3
"""将 Markdown 文件转换为 PDF（使用 reportlab，无需系统依赖）"""

import os
import re
import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Preformatted, KeepTogether, ListFlowable, ListItem
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


def register_chinese_fonts():
    """注册中文字体"""
    font_paths = [
        ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
        ("/System/Library/Fonts/STHeiti Light.ttc", "STHeiti"),
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", "Hiragino"),
        ("/Library/Fonts/Arial Unicode.ttf", "ArialUnicode"),
    ]

    for path, name in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue

    # 如果找不到中文字体，使用默认的 Helvetica（英文）
    return "Helvetica"


def parse_markdown_elements(md_content):
    """解析 Markdown 内容，返回元素列表"""
    html = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'nl2br'])

    elements = []

    # 分割 HTML 标签
    parts = re.split(r'(</?[^>]+>)', html)
    parts = [p for p in parts if p.strip()]

    i = 0
    current_text = ""
    in_code = False
    in_table = False
    table_rows = []
    in_list = False
    list_items = []
    list_type = "ul"

    while i < len(parts):
        tag = parts[i].strip()

        if tag == '<table>':
            if current_text:
                elements.append(('p', current_text))
                current_text = ""
            in_table = True
            table_rows = []
            i += 1
            continue

        elif tag == '</table>':
            in_table = False
            if table_rows:
                elements.append(('table', table_rows))
            table_rows = []
            i += 1
            continue

        elif tag == '<tr>':
            i += 1
            continue

        elif tag == '</tr>':
            i += 1
            continue

        elif tag in ['<th>', '<td>']:
            # 获取单元格内容
            i += 1
            cell_content = ""
            while i < len(parts) and parts[i].strip() not in ['</th>', '</td>']:
                cell_content += parts[i]
                i += 1
            if table_rows:
                table_rows[-1].append(cell_content.strip())
            else:
                table_rows.append([cell_content.strip()])
            i += 1
            continue

        elif tag.startswith('<h') and tag[2].isdigit() and tag[3] == '>':
            level = int(tag[2])
            if current_text:
                elements.append(('p', current_text))
                current_text = ""
            i += 1
            title = ""
            while i < len(parts) and not parts[i].strip().startswith(f'</h{level}>'):
                title += parts[i]
                i += 1
            elements.append((f'h{level}', title.strip()))
            i += 1
            continue

        elif tag == '<pre>':
            if current_text:
                elements.append(('p', current_text))
                current_text = ""
            i += 1
            code_content = ""
            while i < len(parts) and parts[i].strip() != '</pre>':
                code_content += parts[i]
                i += 1
            # 清理 code 标签
            code_content = re.sub(r'</?code[^>]*>', '', code_content)
            code_content = code_content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
            elements.append(('code', code_content))
            i += 1
            continue

        elif tag in ['<ul>', '<ol>']:
            if current_text:
                elements.append(('p', current_text))
                current_text = ""
            in_list = True
            list_type = 'ol' if tag == '<ol>' else 'ul'
            list_items = []
            i += 1
            continue

        elif tag in ['</ul>', '</ol>']:
            in_list = False
            if list_items:
                elements.append((list_type, list_items))
            list_items = []
            i += 1
            continue

        elif tag == '<li>':
            i += 1
            li_content = ""
            while i < len(parts) and parts[i].strip() != '</li>':
                li_content += parts[i]
                i += 1
            list_items.append(li_content.strip())
            i += 1
            continue

        elif tag == '<hr>':
            if current_text:
                elements.append(('p', current_text))
                current_text = ""
            elements.append(('hr', ''))
            i += 1
            continue

        elif tag == '<blockquote>':
            if current_text:
                elements.append(('p', current_text))
                current_text = ""
            i += 1
            quote_content = ""
            while i < len(parts) and parts[i].strip() != '</blockquote>':
                quote_content += parts[i]
                i += 1
            elements.append(('blockquote', quote_content.strip()))
            i += 1
            continue

        elif tag.startswith('<') and not tag.startswith('</'):
            # 其他开始标签，跳过
            i += 1
            continue

        elif tag.startswith('</'):
            # 结束标签，跳过
            i += 1
            continue

        else:
            current_text += tag
            i += 1

    if current_text:
        elements.append(('p', current_text))

    return elements


def clean_html(text):
    """清理 HTML 标签，保留基本格式"""
    # 替换常见 HTML 实体
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    text = text.replace('&quot;', '"').replace('&apos;', "'")
    text = text.replace('&nbsp;', ' ')

    # 处理 strong/em
    text = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', text)
    text = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', text)
    text = re.sub(r'<code>(.*?)</code>', r'<font face="Courier">\1</font>', text)

    # 移除其他 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)

    return text.strip()


def md_to_pdf(md_path, pdf_path):
    """将单个 Markdown 文件转换为 PDF"""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 解析元素
    elements = parse_markdown_elements(md_content)

    # 注册字体
    chinese_font = register_chinese_fonts()

    # 创建文档
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    # 定义样式
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ChineseTitle',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=20,
        leading=28,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=20,
        spaceBefore=0,
        borderWidth=0,
        borderColor=colors.HexColor('#2c3e50'),
        borderPadding=10,
    )

    h1_style = ParagraphStyle(
        'ChineseH1',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=18,
        leading=26,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=14,
        spaceBefore=20,
        borderWidth=2,
        borderColor=colors.HexColor('#2c3e50'),
        borderPadding=8,
    )

    h2_style = ParagraphStyle(
        'ChineseH2',
        parent=styles['Heading2'],
        fontName=chinese_font,
        fontSize=15,
        leading=22,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=16,
        leftIndent=0,
        borderWidth=0,
        borderColor=colors.HexColor('#3498db'),
        borderPadding=6,
    )

    h3_style = ParagraphStyle(
        'ChineseH3',
        parent=styles['Heading3'],
        fontName=chinese_font,
        fontSize=13,
        leading=19,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=14,
    )

    h4_style = ParagraphStyle(
        'ChineseH4',
        parent=styles['Heading4'],
        fontName=chinese_font,
        fontSize=12,
        leading=17,
        textColor=colors.HexColor('#555555'),
        spaceAfter=8,
        spaceBefore=12,
    )

    body_style = ParagraphStyle(
        'ChineseBody',
        parent=styles['Normal'],
        fontName=chinese_font,
        fontSize=10.5,
        leading=17,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8,
        alignment=TA_JUSTIFY,
    )

    code_style = ParagraphStyle(
        'ChineseCode',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#333333'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=10,
        rightIndent=10,
        backColor=colors.HexColor('#f8f8f8'),
        borderWidth=1,
        borderColor=colors.HexColor('#3498db'),
        borderPadding=8,
    )

    quote_style = ParagraphStyle(
        'ChineseQuote',
        parent=styles['Normal'],
        fontName=chinese_font,
        fontSize=10.5,
        leading=17,
        textColor=colors.HexColor('#555555'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=15,
        borderWidth=0,
        borderColor=colors.HexColor('#3498db'),
        borderPadding=8,
        backColor=colors.HexColor('#f8f9fa'),
    )

    # 构建 PDF 内容
    story = []
    first_heading = True

    for elem_type, elem_content in elements:
        if elem_type == 'h1':
            if not first_heading:
                story.append(PageBreak())
            first_heading = False
            text = clean_html(elem_content)
            story.append(Paragraph(text, h1_style))
            story.append(Spacer(1, 6))

        elif elem_type == 'h2':
            text = clean_html(elem_content)
            story.append(Paragraph(text, h2_style))
            story.append(Spacer(1, 4))

        elif elem_type == 'h3':
            text = clean_html(elem_content)
            story.append(Paragraph(text, h3_style))
            story.append(Spacer(1, 3))

        elif elem_type == 'h4':
            text = clean_html(elem_content)
            story.append(Paragraph(text, h4_style))
            story.append(Spacer(1, 2))

        elif elem_type == 'p':
            text = clean_html(elem_content)
            if text:
                story.append(Paragraph(text, body_style))

        elif elem_type == 'code':
            text = elem_content.strip()
            if text:
                story.append(Preformatted(text, code_style))

        elif elem_type == 'blockquote':
            text = clean_html(elem_content)
            if text:
                story.append(Paragraph(text, quote_style))

        elif elem_type == 'hr':
            story.append(Spacer(1, 10))
            story.append(Table([['']], colWidths=[16 * cm], style=TableStyle([
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#dddddd')),
            ])))
            story.append(Spacer(1, 10))

        elif elem_type == 'table':
            rows = elem_content
            if not rows:
                continue

            # 构建表格数据
            table_data = []
            for row in rows:
                cleaned_row = [clean_html(cell) for cell in row]
                table_data.append(cleaned_row)

            if not table_data:
                continue

            # 计算列宽
            num_cols = max(len(row) for row in table_data) if table_data else 1
            col_width = 16 * cm / num_cols

            # 确保每行列数一致
            for row in table_data:
                while len(row) < num_cols:
                    row.append('')

            # 创建表格
            table = Table(table_data, colWidths=[col_width] * num_cols)

            # 表格样式
            table_style = TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), chinese_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ])

            # 表头样式
            if table_data:
                table_style.add('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5'))
                table_style.add('FONTNAME', (0, 0), (-1, 0), chinese_font)
                table_style.add('FONTSIZE', (0, 0), (-1, 0), 9)
                table_style.add('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2c3e50'))

            # 隔行变色
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafafa'))

            table.setStyle(table_style)
            story.append(Spacer(1, 8))
            story.append(table)
            story.append(Spacer(1, 8))

        elif elem_type in ['ul', 'ol']:
            items = elem_content
            if items:
                bullet = '•' if elem_type == 'ul' else ''
                for idx, item in enumerate(items):
                    text = clean_html(item)
                    if elem_type == 'ol':
                        prefix = f"{idx + 1}. "
                    else:
                        prefix = "• "
                    story.append(Paragraph(prefix + text, body_style))
                story.append(Spacer(1, 6))

    # 生成 PDF
    doc.build(story)
    print(f"✅ 已生成: {pdf_path}")


def main():
    base_dir = "/Users/yven/PycharmProjects/github/Yuxi/doc-yven"

    files = [
        ("Palantir-AIP-Analyst-深度剖析.md", "Palantir-AIP-Analyst-深度剖析.pdf"),
        ("AbutionGraph-本体智能数据库.md", "AbutionGraph-本体智能数据库.pdf"),
        ("知识图谱之本体结构与语义解耦-蚂蚁集团实践.md", "知识图谱之本体结构与语义解耦-蚂蚁集团实践.pdf"),
        ("从知识图谱到本体模型-本体论建模认识论过程.md", "从知识图谱到本体模型-本体论建模认识论过程.pdf"),
    ]

    for md_name, pdf_name in files:
        md_path = os.path.join(base_dir, md_name)
        pdf_path = os.path.join(base_dir, pdf_name)
        if os.path.exists(md_path):
            try:
                md_to_pdf(md_path, pdf_path)
            except Exception as e:
                print(f"❌ 生成失败 {pdf_name}: {e}")
        else:
            print(f"⚠️ 文件不存在: {md_path}")


if __name__ == "__main__":
    main()
