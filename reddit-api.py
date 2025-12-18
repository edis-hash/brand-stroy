import praw
import google.generativeai as genai
import os

# ================= 配置区域 (请填入你的 Key) =================
# 1. Google Gemini API 设置 (https://aistudio.google.com/app/apikey)
GOOGLE_API_KEY = "你的_GOOGLE_API_KEY"  # 替换这里

# 2. Reddit API 设置 (https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID = "你的_REDDIT_CLIENT_ID"     # 替换这里
REDDIT_CLIENT_SECRET = "你的_REDDIT_SECRET"    # 替换这里
REDDIT_USER_AGENT = "AmazonTrendBot/2.0 (Gemini)"

# ==========================================================

class AmazonTrendAgent:
    def __init__(self):
        # 配置 Gemini
        genai.configure(api_key=GOOGLE_API_KEY)
        # 使用 gemini-1.5-flash，速度快且免费额度高，上下文极其巨大
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 配置 Reddit
        self.reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
        print("🤖 Google Gemini 智能体初始化完成...")

    def translate_to_english(self, chinese_keyword):
        """Step 1: 将中文输入转化为英文搜索词"""
        print(f"🔄 正在调用 Gemini 翻译关键词: {chinese_keyword}...")
        
        prompt = f"You are a translator. Translate '{chinese_keyword}' to a single English keyword or phrase suitable for Reddit search. Only output the English text, nothing else."
        
        response = self.model.generate_content(prompt)
        eng_keyword = response.text.strip()
        print(f"✅ 英文搜索词: {eng_keyword}")
        return eng_keyword

    def scrape_reddit_data(self, keyword, limit=50):
        """Step 2: 抓取 Reddit 数据"""
        print(f"🕵️ 正在 Reddit 上挖掘 '{keyword}' 的相关数据 (Top {limit} posts)...")
        
        # 扩大搜索范围，因为 Gemini 吃得下！
        target_subreddits = "all+NFL+HomeDecorating+Plushies+Gifts+PartyPlanning+DIY"
        subreddit = self.reddit.subreddit(target_subreddits)
        
        posts_data = []
        try:
            for submission in subreddit.search(keyword, sort='relevance', time_filter='month', limit=limit):
                # 构建结构化数据
                post_content = f"--- POST START ---\nTitle: {submission.title}\nSubreddit: {submission.subreddit.display_name}\nScore: {submission.score}"
                
                # 获取更多评论，因为 Gemini 上下文很大，我们可以多拿一点
                submission.comments.replace_more(limit=0)
                top_comments = ""
                for comment in submission.comments.list()[:5]: # 增加到前5条评论
                    top_comments += f"\n- Comment (Score {comment.score}): {comment.body}"
                
                full_text = post_content + "\nTop Comments:" + top_comments + "\n--- POST END ---\n"
                posts_data.append(full_text)
        except Exception as e:
            print(f"⚠️ 抓取过程中出现小错误 (可忽略): {e}")

        print(f"📦 成功抓取 {len(posts_data)} 条讨论帖，准备投喂给 Gemini。")
        return "\n".join(posts_data)

    def analyze_trends(self, data_text, original_topic):
        """Step 3: 使用 Gemini 进行选品分析"""
        print("🧠 正在调用 Gemini 1.5 Flash 进行深度分析...")
        
        # Gemini 1.5 Flash 拥有 100万 token 上下文，不需要像 OpenAI 那样截断数据
        # 我们可以直接把整个巨大的文本扔进去
        
        prompt = f"""
        你是一位专业的亚马逊选品专家。你要为主题“{original_topic}”分析以下来自 Reddit 的原始讨论数据。
        
        请输出一份结构清晰的【亚马逊选品洞察报告】，包含以下部分（请用中文回答）：
        
        1. **🔥 飙升关键词 (Top 5 Keywords)**: 
           - 重点挖掘形容词+名词的组合（例如 "Sparkly Helmet", "Weighted Plush"）。
           - 排除像 "Super Bowl" 这种过于宽泛的大词，找具体的长尾词/产品属性词。
           
        2. **😫 用户痛点深度挖掘 (Pain Points)**:
           - 用户在抱怨什么？（例如：“找不到这个颜色的装饰”，“公仔太硬了”，“送礼没新意”）。
           - 引用一两个具体的评论内容佐证。
           
        3. **💡 落地选品建议 (Actionable Products)**:
           - **针对【装饰品】类目**推荐 1 个具体产品方向（包含材质、颜色、风格建议）。
           - **针对【毛绒玩具】类目**推荐 1 个具体产品方向（包含功能、触感、人群建议）。
           - *必须说明该产品解决了什么痛点。*

        4. **🔍 流量验证指令**:
           - 给出 3 个英文搜索词，以便我去 Google Trends 或 Amazon ABA 验证。

        以下是 Reddit 数据：
        {data_text}
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"❌ 分析失败: {e}"

    def run(self, topic):
        print("="*50)
        print(f"🚀 Amazon Trend Agent (Gemini版) 启动 - 目标: {topic}")
        print("="*50)
        
        # 1. 翻译
        eng_keyword = self.translate_to_english(topic)
        
        # 2. 抓取
        raw_data = self.scrape_reddit_data(eng_keyword, limit=60) # 稍微增加抓取量
        
        if not raw_data:
            print("❌ 未找到足够的数据。")
            return

        # 3. 分析
        report = self.analyze_trends(raw_data, topic)
        
        print("\n" + "="*20 + " 📊 Gemini 选品报告 " + "="*20 + "\n")
        print(report)
        print("\n" + "="*60)
        print("✅ SOP 执行完毕。由 Google Gemini 驱动。")

# ================= 执行入口 =================
if __name__ == "__main__":
    agent = AmazonTrendAgent()
    user_input = input("请输入你想挖掘的主题 (中文，例如: 超级碗 / 情人节 / 露营): ")
    if user_input:
        agent.run(user_input)
