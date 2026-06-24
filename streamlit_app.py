"""streamlit_app.py — NeuroDEG Streamlit 网页界面"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis.loader import load_deg
from analysis.filter import filter_degs, get_volcano_data
from analysis.neural_matcher import load_knowledge_base, match_neural_types, match_pathways
from analysis.enrichment import run_enrichment
from analysis.interpreter import render_report, generate_interpretations
from agent_core.trace import TraceRecorder
from agent_core.guardrails import check_output_guardrails
from agent_core.quality import QualityEvaluator
from agent_core.memory import save_run
from agent_core.state import AgentState
from agent_core.chat import query_gene, query_cell_type

st.set_page_config(page_title="NeuroDEG", layout="wide", page_icon="🧬")

# ====== Home header ======
st.markdown("""
<div style="text-align:center; margin-bottom:20px;">
    <h1 style="color:#FF6B35; margin:0;">NeuroDEG — 神经细胞表达差异分析 Agent</h1>
    <p style="color:#666; margin:8px 0 0 0; font-size:16px;">根据 DEG 数据自动识别神经细胞类型、匹配通路、生成带 Agent Trace 的结构化报告</p>
</div>
""", unsafe_allow_html=True)

# Feature highlights
feat1, feat2, feat3, feat4 = st.columns(4)
with feat1:
    st.markdown("🧠 **9 种细胞类型**\n\n兴奋性/抑制性神经元\n胶质细胞·多巴胺能·胆碱能·血清素能")
with feat2:
    st.markdown("🔬 **1214 条 GO 通路**\n\n超几何检验 + FDR 校正\n本地 + Enrichr API 富集")
with feat3:
    st.markdown("📊 **全自动分析**\n\n火山图·细胞类型匹配\n富集分析·结构化报告")
with feat4:
    st.markdown("🤖 **Agent 管道**\n\nTool Trace·Guardrails\n质量评估·追问")

st.divider()

# 操作提示
st.markdown("""
<div style="background-color:#FF6B35; padding:12px 20px; border-radius:8px; text-align:center;">
    <span style="color:white; font-size:16px;">👈 在侧边栏选择数据来源和参数，然后点击 <strong>开始分析</strong></span>
</div>
""", unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    with st.expander("📚 知识库信息", expanded=False):
        st.markdown("""
        **🧠 9 种神经细胞类型**
        | 数据源 | 细胞类型数 | 标记基因数 |
        |:------|:---------:|:---------:|
        | Curated 知识库 | 9 | 87 |
        | PanglaoDB 补充 | 27 | 785 |
        | **合计** | **36** | **872** |

        **Curated 9 种:** 兴奋性/抑制性神经元 · 星形胶质细胞 · 小胶质细胞 · 少突胶质细胞 · 神经干细胞 · 多巴胺能/胆碱能/血清素能神经元
        
        **PanglaoDB 补充 27 种:** Interneurons · Astrocytes · Oligodendrocytes · Microglia · Purkinje neurons · Pyramidal cells · GABAergic/Glutaminergic neurons · 等
        
        **🔬 15 条神经通路**
        | 通路 | KEGG |
        |:----|:----:|
        | 谷氨酸能突触 | hsa04724 |
        | GABA能突触 | hsa04727 |
        | 多巴胺能突触 | hsa04728 |
        | 胆碱能突触 | hsa04725 |
        | 5-羟色胺能突触 | hsa04726 |
        | 长时程增强(LTP) | hsa04720 |
        | 神经营养因子 | hsa04722 |
        | 神经炎症 | — |
        | 反应性胶质增生 | — |
        | 髓鞘形成 | — |
        | 神经发生 | — |
        | 突触囊泡循环 | hsa04721 |
        | 钙信号 | hsa04020 |
        | 自噬-溶酶体 | hsa04140 |
        | 氧化应激 | — |
        
        **📖 数据来源**
        - CellMarker 数据库
        - PanglaoDB 单细胞标记基因库
        - Allen Brain Atlas
        - GeneCards / NCBI
        - KEGG 通路
        - GO 本体 (Gene Ontology)
        """)
    
    st.header("设置")
    data_option = st.radio("数据来源", ["示例数据", "上传文件"])
    
    uploaded_file = None
    if data_option == "上传文件":
        uploaded_file = st.file_uploader("选择DEG文件", type=["csv", "tsv"])
    
    fc_cutoff = st.number_input("|log2FC| 阈值", min_value=0.0, max_value=5.0, value=1.0, step=0.5)
    p_cutoff = st.number_input("padj 阈值", min_value=0.0, max_value=1.0, value=0.05, step=0.01, format="%.3f")
    use_api = st.checkbox("启用 Enrichr API 富集", value=False)
    
    run_btn = st.button("开始分析", type="primary")

# 初始化 session state
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

if run_btn or st.session_state.analyzed:
    # 加载数据
    if data_option == "示例数据" or (not uploaded_file and st.session_state.analyzed):
        example_path = os.path.join(os.path.dirname(__file__), "data", "example_neuro_deg.csv")
        if not os.path.exists(example_path):
            st.error("示例数据文件不存在")
            st.stop()
        input_path = example_path
        input_name = "example_neuro_deg.csv"
    elif uploaded_file:
        os.makedirs(os.path.join(os.path.dirname(__file__), "input"), exist_ok=True)
        save_path = os.path.join(os.path.dirname(__file__), "input", uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        input_path = save_path
        input_name = uploaded_file.name
    else:
        st.stop()

    trace = TraceRecorder()
    state = None
    
    try:
        st1 = trace.start("Input Checker")
        df = load_deg(input_path)
        trace.finish(st1, "success", {"genes": len(df)})
        
        st2 = trace.start("DEG Filter")
        filter_result = filter_degs(df, fc_cutoff, p_cutoff)
        trace.finish(st2, "success", filter_result["summary"])
        
        sig_count = filter_result["summary"]["significant"]
        match_result = {"results": [], "total_matched_types": 0}
        
        if sig_count >= 10:
            st3 = trace.start("Neural Matcher", decision=f"显著基因{sig_count}>=10")
            kb, g2c = load_knowledge_base()
            match_result = match_neural_types(filter_result["up"], filter_result["down"], kb, g2c)
            trace.finish(st3, "success", {"matched_types": match_result["total_matched_types"]})
            
            st4 = trace.start("Enrichment")
            all_genes = set(filter_result["all"]["gene"].tolist())
            enrichment_result = run_enrichment(list(all_genes), use_api=use_api)
            trace.finish(st4, "success", {"local_pathways": len(enrichment_result["local"])})
        else:
            trace.start("Neural Matcher", decision="跳过: 显著基因不足")
            trace.finish(trace.steps[-1], "skipped")
            enrichment_result = {"local": [], "api": None}
        
        st5 = trace.start("Report Generator")
        report = render_report(filter_result, match_result, enrichment_result, input_file=input_name, output_path=None)
        trace.finish(st5, "success")
        
        guard_warnings = check_output_guardrails(report)
        qe = QualityEvaluator()
        quality = qe.evaluate(filter_result, match_result, guard_warnings)
        
        st.session_state.analyzed = True
        st.session_state.df = df
        st.session_state.input_name = input_name
        st.session_state.filter_result = filter_result
        st.session_state.match_result = match_result
        st.session_state.enrichment_result = enrichment_result
        st.session_state.report = report
        st.session_state.trace = trace
        st.session_state.quality = quality
        st.session_state.guard_warnings = guard_warnings
        
    except Exception as e:
        st.error(f"分析失败: {e}")
        st.stop()

# 显示结果
if st.session_state.analyzed:
    tr = st.session_state.trace
    fr = st.session_state.filter_result
    mr = st.session_state.match_result
    er = st.session_state.enrichment_result
    rp = st.session_state.report
    ql = st.session_state.quality
    gw = st.session_state.guard_warnings
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "火山图", "Agent Trace", "细胞类型", "通路富集", "报告", "质量评估", "Ask Agent"
    ])
    
    with tab1:
        st.subheader("火山图")
        from utils.visualizer import plot_volcano
        vdata = get_volcano_data(st.session_state.df, fc_cutoff, p_cutoff)
        import tempfile
        tmp = os.path.join(tempfile.gettempdir(), "neurodeg_volcano.png")
        plot_volcano(vdata, tmp, title=f"Volcano (|log2FC|>{fc_cutoff}, padj<{p_cutoff})", fc_cutoff=fc_cutoff, p_cutoff=p_cutoff)
        st.image(tmp)
        
        st.subheader("筛选摘要")
        
        st.subheader("筛选摘要")
        s = fr["summary"]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总基因数", s["total_genes"])
        col2.metric("显著差异", s["significant"])
        col3.metric("上调", s["up"])
        col4.metric("下调", s["down"])
    
    with tab2:
        st.subheader("Agent Trace — 步骤决策")
        st.markdown(tr.format_table())
    
    with tab3:
        st.subheader("神经细胞类型匹配")
        if mr["results"]:
            from utils.visualizer import plot_cell_type_bar
            import tempfile
            tmp = os.path.join(tempfile.gettempdir(), "neurodeg_ct_bar.png")
            plot_cell_type_bar(mr, tmp)
            st.image(tmp)
            
            for ct in mr["results"]:
                with st.expander(f"{ct['type']} ({ct['matched']}/{ct['total_markers']} 标记)"):
                    st.write(f"上调: {ct['up_genes'] or '无'}")
                    st.write(f"下调: {ct['down_genes'] or '无'}")
                    st.write(f"解读: {ct['interpretation']}")
                    if ct['disease_hints']:
                        st.write(f"疾病关联: {ct['disease_hints']}")
        else:
            st.info("未检测到显著的神经细胞标记基因变化")
    
    with tab4:
        st.subheader("通路富集分析")
        
        # GO 富集结果
        if er.get("go"):
            st.markdown(f"**GO 神经通路富集**（超几何检验 + FDR 校正）— 共 {len(er['go'])} 条")
            go_df = pd.DataFrame([{
                "通路": g["go_name"][:40],
                "重叠": g["ratio"],
                "P值": f"{g['p_value']:.2e}",
                "校正P值": f"{g['adjusted_p_value']:.2e}",
                "基因": ", ".join(g["overlap_genes"][:5])
            } for g in er["go"][:15]])
            st.dataframe(go_df, use_container_width=True, hide_index=True)
        else:
            st.info("GO 富集未找到显著结果\n（需要 data/go.obo + data/goa_human.gaf.gz）")
        
        st.divider()
        
        # 本地通路匹配
        if er["local"]:
            st.markdown(f"**本地通路匹配** — 共 {len(er['local'])} 条")
            for pw in er["local"][:10]:
                st.markdown(f"**{pw['pathway_name']}** — {pw.get('overlap_ratio', '')}")
                st.markdown(f"匹配基因: {pw['matched_genes']}")
                st.markdown(f"{pw.get('biological_process', '')}")
                st.divider()
        else:
            st.info("未发现显著富集的通路")
        if er.get("api") and er["api"]:
            st.subheader("Enrichr API 结果")
            st.dataframe(er["api"])
    
    with tab5:
        st.subheader("完整分析报告")
        st.markdown(rp)
    
    with tab6:
        st.subheader("质量评估")
        st.markdown(f"**等级:** {ql['grade']}")
        st.markdown(f"**原因:** {'; '.join(ql['reasons'])}")
        if gw:
            st.warning("Guardrails 警告:")
            for w in gw:
                st.warning(w['message'])
        else:
            st.success("Guardrails 检查通过")
    
    with tab7:
        st.subheader("🔍 分析延伸 — 追问分析结果")
        st.markdown("基于本次分析结果，从不同角度深入了解潜在的生物学意义：\n")
        
        from agent_core.qa_buttons import pathway_insights, drug_association, analysis_summary
        
        col_b1, col_b2, col_b3 = st.columns(3)
        
        with col_b1:
            btn1 = st.button("🧬 通路功能解读", use_container_width=True)
        with col_b2:
            btn2 = st.button("💊 药物-靶点关联", use_container_width=True)
        with col_b3:
            btn3 = st.button("📄 导出分析摘要", use_container_width=True)
        
        st.divider()
        
        if "active_tab7_btn" not in st.session_state:
            st.session_state.active_tab7_btn = None
        
        if btn1:
            st.session_state.active_tab7_btn = "insights"
        elif btn2:
            st.session_state.active_tab7_btn = "drugs"
        elif btn3:
            st.session_state.active_tab7_btn = "summary"
        
        if st.session_state.active_tab7_btn == "insights":
            with st.spinner("分析通路功能关联..."):
                try:
                    result = pathway_insights(
                        st.session_state.enrichment_result.get("go", []),
                        st.session_state.match_result,
                        st.session_state.enrichment_result.get("local", [])
                    )
                    st.markdown(result)
                except Exception as e:
                    st.error(f"分析失败: {e}")
        
        elif st.session_state.active_tab7_btn == "drugs":
            with st.spinner("检索药物靶点关联..."):
                try:
                    result = drug_association(
                        st.session_state.enrichment_result.get("go", []),
                        st.session_state.enrichment_result.get("local", [])
                    )
                    st.markdown(result)
                except Exception as e:
                    st.error(f"检索失败: {e}")
        
        elif st.session_state.active_tab7_btn == "summary":
            try:
                s = st.session_state.filter_result["summary"]
                result = analysis_summary(
                    st.session_state.filter_result,
                    st.session_state.match_result,
                    st.session_state.enrichment_result,
                    st.session_state.quality,
                    input_file=st.session_state.get("input_name", ""),
                    fc_cutoff=s.get("fc_cutoff", 1.0),
                    p_cutoff=s.get("p_cutoff", 0.05)
                )
                st.code(result, language="text")
                st.markdown("点击右上角复制按钮或选中文本后 Ctrl+C 复制")
            except Exception as e:
                st.error(f"生成摘要失败: {e}")
        
        # Also keep the original gene query in an expander
        with st.expander("🔬 查询特定基因或细胞类型", expanded=False):
            question = st.text_input("输入基因名或细胞类型", placeholder="例如: GFAP 或 星形胶质细胞")
            if question:
                try:
                    from agent_core.chat import query_gene, query_cell_type, load_kb
                    kb = load_kb()
                    answer = ""
                    for ct_type in ["兴奋性神经元", "抑制性神经元", "星形胶质细胞", "小胶质细胞", 
                                    "少突胶质细胞", "神经干细胞", "多巴胺能神经元", "胆碱能神经元", "血清素能神经元"]:
                        if ct_type in question:
                            direction = "up" if "上调" in question else ("down" if "下调" in question else "")
                            answer = query_cell_type(ct_type, direction, kb)
                            break
                    if not answer:
                        for ct in kb["cell_types"]:
                            for m in ct["markers"]:
                                if m["gene"].upper() in question.upper():
                                    answer = query_gene(m["gene"], kb)
                                    break
                            if answer:
                                break
                    if answer:
                        st.markdown(answer)
                    else:
                        st.info("未找到匹配信息")
                except Exception as e:
                    st.error(f"查询失败: {e}")
        
        # Also store input_name for summary
        if "input_name" not in st.session_state:
            st.session_state.input_name = input_name if "input_name" in dir() else ""
