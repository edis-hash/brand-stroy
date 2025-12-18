import streamlit as st
import praw
import google.generativeai as genai
import time

# ================= 配置区域 (请填入你的 Key) =================
# 【安全提示】在正式部署时，建议使用 st.secrets 来管理这些敏感信息，不要直接写在代码里。
GOOGLE_API_KEY = "你的_GOOGLE_API_KEY"  # 替换这里
REDDIT_CLIENT_ID = "你的_REDDIT_CLIENT_ID"     # 替换这里
REDDIT_CLIENT_SECRET = "你的_REDDIT_SECRET"    # 替换这里
REDDIT_USER_AGENT = "AmazonTrendBot/StreamlitUI/1.0"
# ==========================================================

# 设置页面标题和图标
st.set_page_config(
    page_title="亚马逊选品趋势智能体",
    page_icon="🛍️",
    layout="centered"
)

# 缓存资源：确保 Reddit 和 Gemini 客户端只初始化一次，提高运行效率
@st.cache_resource
def get_agents():
    # 配置 Gemini
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 配置 Reddit
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=RED_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    return model, reddit

# 获取初始化的智能体
try:
    model_agent, reddit_agent = get_agents()
    st.sidebar.success("API 代理连接成功!")
except Exception as e:
    st.sidebar.error(f"API 连接失败，请检查 Keys: {e}")
    st.stop()


# --- 核心功能函数 (从之前的 Class 改写为独立函数) ---

def translate_to_english(chinese_keyword):
    """Step 1: 使用 Gemini 翻译"""
    prompt = f"You are a translator. Translate '{chinese_keyword}' to a single English keyword or phrase suitable for Reddit search. Only output the English text, nothing else."
    response = model_agent.generate_content(prompt)
    return response.text.strip()

def scrape_reddit_data(keyword, limit=60):
    """Step 2: 抓取 Reddit 数据"""
    # 扩大搜索范围
    target_subreddits = "all+NFL+HomeDecorating+Plushies+Gifts+PartyPlanning+DIY+Toys"
    subreddit = reddit_agent.subreddit(target_subreddits)
    
    posts_data = []
    try:
        # 使用 st.status 显示抓取进度 (Streamlit 特性)
        with st.status(f"正在 Reddit 上挖掘 '{keyword}'...", expanded=True) as status:
            count = 0
            st.write("连接 Reddit API...")
            search_results = subreddit.search(keyword, sort='relevance', time_filter='month', limit=limit)
            
            st.write("开始抓取帖子和评论...")
            for submission in search_results:
                count += 1
                # 构建结构化数据
                post_content = f"--- POST START ---\nTitle: {submission.title}\nSubreddit: {submission.subreddit.display_name}\nScore: {submission.score}"
                
                submission.comments.replace_more(limit=0)
                top_comments = ""
                # 抓取前 5 条高赞评论
                for comment in submission.comments.list()[:5]: 
                    top_comments += f"\n- Comment (Score {comment.score}): {comment.body}"
                
                full_text = post_content + "\nTop Comments:" + top_comments + "\n--- POST END ---\n"
                posts_data.append(full_text)
                
                if count % 10 == 0:
                    st.write(f"已抓取 {count} 条帖子...")
                    
            status.update(label=f"抓取完成！共 {len(posts_data)} 条有效数据。", state="complete", expanded=False)
            
    except Exception as e:
        st.error(f"抓取过程中出错: {e}")
        return None

    return "\n".join(posts_data) if posts_data else None

def analyze_trends(data_text, original_topic):
    """Step 3: 使用 Gemini 进行选品分析"""
    prompt = f"""
    你是一位专业的亚马逊选品专家。你要为主题“{original_topic}”分析以下来自 Reddit 的原始讨论数据。
    
    请输出一份结构清晰的【亚马逊选品洞察报告】，包含以下部分（请用中文回答，使用 Markdown 格式）：
    
    ### 1. 🔥 飙升关键词 (Top 5 Keywords)
    - 重点挖掘形容词+名词的组合（例如 "Sparkly Helmet", "Weighted Plush"）。
    - 排除像 "{original_topic}" 这种过于宽泛的大词，找具体的长尾词/产品属性词。
       
    ### 2. 😫 用户痛点深度挖掘 (Pain Points)
    - 用户在抱怨什么？（例如：“找不到这个颜色的装饰”，“公仔太硬了”，“送礼没新意”）。
    - *请务必引用一两个具体的评论内容佐证。*
       
    ### 3. 💡 落地选品建议 (Actionable Products)
    - **针对【装饰品】类目**推荐 1 个具体产品方向（包含材质、颜色、风格建议）。
    - **针对【毛绒玩具/礼物】类目**推荐 1 个具体产品方向（包含功能、触感、人群建议）。
    - *必须说明该产品解决了什么痛点。*

    ### 4. 🔍 流量验证指令
    - 给出 3 个英文搜索词，以便我去 Google Trends 或 Amazon ABA 验证。

    以下是 Reddit 数据：
    {data_text}
    """
    try:
        response = model_agent.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ 分析失败: {e}"

# ================= UI 界面构建 =================

st.title("🛍️ 亚马逊选品趋势智能体")
st.markdown("基于 **Reddit 舆情** + **Google Gemini** 大模型的自动化 SOP 挖掘工具。")

# 侧边栏说明
with st.sidebar:
    st.header("使用说明")
    st.markdown("""
    1. 在右侧输入框输入你想挖掘的主题（中文即可）。
    2. 点击“开始全流程挖掘”按钮。
    3. 系统将自动执行：翻译 -> 抓取 Reddit 数据 -> AI 深度分析。
    4. 耐心等待报告生成。
    """)
    st.info("由 gemini-1.5-flash 模型驱动")

# 主要输入区
topic_input = st.text_input("请输入主题关键词 (例如: 超级碗 / 万圣节 / 露营)", placeholder="在这里输入...")
run_button = st.button("🚀 开始全流程挖掘", type="primary")

st.divider()

# 主逻辑区域
if run_button:
    if not topic_input.strip():
        st.warning("请先输入一个主题关键词！")
    else:
        # 1. 翻译阶段
        with st.spinner("正在思考并翻译关键词..."):
            eng_keyword = translate_to_english(topic_input)
        st.success(f"✅ 英文搜索词已确认为: **{eng_keyword}**")
        
        # 2. 抓取阶段 (函数内部包含了 st.status 显示进度)
        raw_data = scrape_reddit_data(eng_keyword, limit=70)
        
        if not raw_data:
            st.error("❌ 未能找到足够的数据。请尝试更换关键词。")
        else:
            # 3. 分析阶段
            with st.spinner("🧠 Gemini 大脑正在进行深度分析 (这可能需要 30-60 秒，请耐心等待)..."):
                # 稍微模拟一点延迟感
                time.sleep(1)
                report = analyze_trends(raw_data, topic_input)
            
            # 结果展示
            st.balloons() # 成功动画效果
            st.subheader(f"📊 关于“{topic_input}”的选品洞察报告")
            st.markdown(report)
            st.success("SOP 执行完毕！请参考上述关键词进行 ABA 验证。")
