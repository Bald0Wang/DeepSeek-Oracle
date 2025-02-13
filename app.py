from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify
from flask_cors import CORS  # 导入 CORS
from llmana.glmapi import GLMClient
from llmana.deepseek_ali_api import DeepSeekClient
from json2ziwei.api import SolarAPI
from json2ziwei.convert import convert_main_json_to_text
from llmana.deepseek_huoshan_api import deepseek_huoshan
import os
import threading
import sqlite3
from datetime import datetime
import time  # 添加 time 模块
from dotenv import load_dotenv  # 添加 dotenv 支持
from token_ana.deepseek_tokenizer import initialize_tokenizer, encode_text

# 加载 .env 文件
load_dotenv()

app = Flask(__name__)
app.secret_key = '9957'  # 用于会话加密
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5000"}})

class StandardizedLLMClient:
    """
    @class StandardizedLLMClient
    @description 标准化大模型客户端接口
    """
    def __init__(self):
        """
        @constructor
        @description 初始化客户端，从环境变量读取配置
        """
        self.api_key = os.getenv('ARK_API_KEY')

        self.client = deepseek_huoshan(self.api_key)
        self.tokenizer = initialize_tokenizer()  # 初始化 tokenizer

    def get_response(self, prompt):
        """
        @method get_response
        @description 获取大模型响应
        @param {str} prompt - 输入提示
        @returns {tuple} - (响应结果, token数量)
        """
        # 计算输入 token 数量
        input_tokens = len(encode_text(prompt, self.tokenizer))
        
        # 获取模型响应
        response = self.client.get_response(prompt)
        
        # 计算输出 token 数量
        output_tokens = len(encode_text(response, self.tokenizer))
        
        return response, input_tokens + output_tokens

# 在需要的地方使用标准化接口
llm_client = StandardizedLLMClient()

@app.route('/', methods=['GET', 'POST'])
def index():
    text_description = ""
    if request.method == 'POST':
        date = request.form.get('date')
        timezone = request.form.get('timezone')
        gender = request.form.get('gender')
        calendar = request.form.get('calendar')  # 获取历法选择

        # 打印调试信息
        print(f"日期: {date}, 时区: {timezone}, 性别: {gender}, 历法: {calendar}")

        # 调用 SolarAPI 获取星盘数据
        solar_api = SolarAPI("http://localhost:3000")
        try:
            json_string = solar_api.get_astrolabe_data(date, int(timezone), gender, is_solar=(calendar == 'solar'))
        except Exception as e:
            text_description = f"请求错误: {e}"
        else:
            main_data = json_string
            text_description = convert_main_json_to_text(main_data)
            session['date'] = date
            session['timezone'] = timezone
            session['gender'] = gender
            session['calendar'] = calendar
            session['text_description'] = text_description

            return redirect(url_for('fortune_telling'))  # 跳转到算命解析页面

    return render_template('index.html', text_description=text_description)

def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect('data.db')  # 使用 data.db 作为数据库文件名
    cursor = conn.cursor()
    
    # 创建 results 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_type TEXT NOT NULL,
            data TEXT NOT NULL,
            date TEXT NOT NULL,
            timezone TEXT NOT NULL,
            gender TEXT NOT NULL,
            calendar TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# 在应用启动时初始化数据库
init_db()

@app.route('/fortune_telling', methods=['GET'])
def fortune_telling():
    # 从 session 中获取数据
    date = session.get('date')
    timezone = session.get('timezone')
    gender = session.get('gender')
    calendar = session.get('calendar')
    text_description = session.get('text_description')
    
    # 检查是否有缓存结果
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT analysis_type, data 
        FROM results 
        WHERE date = ? AND timezone = ? AND gender = ? AND calendar = ?
        ORDER BY timestamp DESC
    """, (date, timezone, gender, calendar))
    
    cached_results = {}
    execution_times = {}  # 初始化执行时间字典
    
    for row in cursor.fetchall():
        analysis_type, result = row
        cached_results[analysis_type] = result
        # 从缓存的结果中提取执行时间
        match = result.split('\n')[0].strip()
        if match.startswith('推理耗时:'):
            try:
                time_str = match.split(':')[1].strip()
                execution_times[analysis_type] = float(time_str.replace('秒', ''))
            except (IndexError, ValueError):
                execution_times[analysis_type] = 0
    
    conn.close()
    
    # 如果有缓存结果，直接返回
    if cached_results:
        return render_template('fortune_telling.html', 
                             date=date, 
                             timezone=timezone, 
                             gender=gender,
                             calendar=calendar, 
                             text_description=text_description, 
                             fortune_results=cached_results,
                             execution_times=execution_times)  # 传递执行时间
    
    # 如果没有缓存结果，进行新的分析
    def thread_target(analysis_type):
        start_time = time.time()
        
        if analysis_type == 'marriage_path':
            response, token_count = llm_client.get_response("参考紫微斗数思路对命主婚姻道路进行分析，命盘如下：  \n" + text_description)
        elif analysis_type == 'challenges':
            response, token_count = llm_client.get_response("参考紫微斗数思路对命主与另一半的困难和挑战进行分析，命盘如下：  \n" + text_description)
        elif analysis_type == 'partner_character':
            response, token_count = llm_client.get_response("参考紫微斗数思路对命主另一半的性格和人品进行分析，命盘如下：  \n" + text_description)
        
        end_time = time.time()
        execution_time = round(end_time - start_time, 2)
        
        # 将结果和统计信息一起存储
        results[analysis_type] = {
            'response': response,
            'execution_time': execution_time,
            'token_count': token_count
        }

    # 创建线程列表
    results = {}
    threads = []
    execution_times = {}  # 用于存储每个分析类型的执行时间

    # 启动三个线程
    for analysis_type in ['marriage_path', 'challenges', 'partner_character']:
        thread = threading.Thread(target=thread_target, args=(analysis_type,))
        threads.append(thread)
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    # 将执行时间添加到结果中
    for analysis_type, result in results.items():
        results[analysis_type] = f"推理耗时: {result['execution_time']}秒\nToken 数量: {result['token_count']}\n\n{result['response']}"

    # 自动生成 Markdown 文件
    markdown_content = "# 紫微斗数算命结果\n\n"
    markdown_content += "## 基本信息\n"
    markdown_content += f"- 日期: {session.get('date')}\n"
    markdown_content += f"- 时区: {session.get('timezone')}\n"
    markdown_content += f"- 性别: {session.get('gender')}\n"
    markdown_content += f"- 历法: {session.get('calendar')}\n\n"
    markdown_content += "## 命盘描述\n"
    markdown_content += f"{session.get('text_description')}\n\n"
    
    for analysis_type, result in results.items():
        # 解析结果字符串
        lines = result.split('\n')
        execution_time = lines[0].split(':')[1].strip().replace('秒', '')
        token_count = lines[1].split(':')[1].strip()
        response = '\n'.join(lines[2:])
        
        markdown_content += f"## {analysis_type.replace('_', ' ').title()} 分析\n"
        markdown_content += f"- 推理耗时: {execution_time}秒\n"
        markdown_content += f"- Token 数量: {token_count}\n"
        markdown_content += f"\n{response}\n\n"
    
    with open("fortune_result.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)

    # 将结果存储到 SQLite 数据库
    conn = sqlite3.connect('data.db')  # 使用 data.db 作为数据库文件名
    cursor = conn.cursor()
    for analysis_type, fortune_result in results.items():
        cursor.execute("""
            INSERT INTO results 
            (analysis_type, data, date, timezone, gender, calendar) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (analysis_type, fortune_result, date, timezone, gender, calendar))
    conn.commit()
    conn.close()

    return render_template('fortune_telling.html', 
                         date=date, 
                         timezone=timezone, 
                         gender=gender,
                         calendar=calendar, 
                         text_description=text_description, 
                         fortune_results=results,
                         execution_times=execution_times)

def generate_markdown(fortune_result):
    """
    @function generate_markdown
    @description 生成包含推理统计信息的 Markdown 文件
    @param {dict} fortune_result - 包含推理结果、时间和 token 数量的字典
    """
    markdown_content = "# 算命结论\n\n"
    for analysis_type, result in fortune_result.items():
        markdown_content += f"## {analysis_type.replace('_', ' ').title()}\n"
        markdown_content += f"- 推理耗时: {result['execution_time']}秒\n"
        markdown_content += f"- Token 数量: {result['token_count']}\n"
        markdown_content += f"\n{result['response']}\n\n"
    
    with open("fortune_result.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)

@app.route('/download_md')
def download_md():
    return send_file("fortune_result.md", as_attachment=True)

def query_database(query):
    """查询数据库并返回结果"""
    # 连接到 SQLite 数据库
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    
    # 执行查询
    cursor.execute(query)
    result = cursor.fetchall()
    
    # 关闭连接
    conn.close()
    return result

def handle_query(query):
    """处理查询并存储结果"""
    result = query_database(query)
    
    # 将结果存储到 SQLite 数据库
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    
    # 假设我们有一个表格叫 'results'，并且它有两列 'data' 和 'timestamp'
    for row in result:
        cursor.execute("INSERT INTO results (data, timestamp) VALUES (?, ?)", (row[0], datetime.now()))
    
    # 提交更改并关闭连接
    conn.commit()
    conn.close()

def on_query_button_click():
    """查询按钮点击事件处理"""
    query = "SELECT * FROM your_table"  # 示例查询
    # 创建并启动线程
    query_thread = threading.Thread(target=handle_query, args=(query,))
    query_thread.start()
    # 这里可以添加代码来更新 UI 或者其他操作

@app.route('/check_cache', methods=['POST'])
def check_cache():
    """检查是否有缓存的结果"""
    data = request.get_json()
    date = data.get('date')
    timezone = data.get('timezone')
    gender = data.get('gender')
    calendar = data.get('calendar')

    # 查询数据库中的缓存结果
    conn = sqlite3.connect('data.db')  # 使用 data.db 作为数据库文件名
    cursor = conn.cursor()
    
    # 假设我们的表结构包含 analysis_type, result, input_params 等字段
    cursor.execute("""
        SELECT analysis_type, data 
        FROM results 
        WHERE date = ? AND timezone = ? AND gender = ? AND calendar = ?
        ORDER BY timestamp DESC
        LIMIT 3
    """, (date, timezone, gender, calendar))
    
    cached_results = {}
    for row in cursor.fetchall():
        analysis_type, result = row
        cached_results[analysis_type] = result
    
    conn.close()
    
    return jsonify({'cached_results': cached_results if cached_results else None})

@app.route('/marriage_path')
def marriage_path():
    # 从数据库获取婚姻道路分析结果
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data FROM results 
        WHERE analysis_type = 'marriage_path' 
        AND date = ? AND timezone = ? AND gender = ? AND calendar = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (session.get('date'), session.get('timezone'), 
          session.get('gender'), session.get('calendar')))
    
    result = cursor.fetchone()
    conn.close()
    
    return render_template('marriage_path.html',
                         date=session.get('date'),
                         timezone=session.get('timezone'),
                         gender=session.get('gender'),
                         calendar=session.get('calendar'),
                         text_description=session.get('text_description'),
                         fortune_result=result[0] if result else None)

@app.route('/challenges')
def challenges():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data FROM results 
        WHERE analysis_type = 'challenges' 
        AND date = ? AND timezone = ? AND gender = ? AND calendar = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (session.get('date'), session.get('timezone'), 
          session.get('gender'), session.get('calendar')))
    
    result = cursor.fetchone()
    conn.close()
    
    return render_template('challenges.html',
                         date=session.get('date'),
                         timezone=session.get('timezone'),
                         gender=session.get('gender'),
                         calendar=session.get('calendar'),
                         text_description=session.get('text_description'),
                         fortune_result=result[0] if result else None)

@app.route('/partner_character')
def partner_character():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data FROM results 
        WHERE analysis_type = 'partner_character' 
        AND date = ? AND timezone = ? AND gender = ? AND calendar = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (session.get('date'), session.get('timezone'), 
          session.get('gender'), session.get('calendar')))
    
    result = cursor.fetchone()
    conn.close()
    
    return render_template('partner_character.html',
                         date=session.get('date'),
                         timezone=session.get('timezone'),
                         gender=session.get('gender'),
                         calendar=session.get('calendar'),
                         text_description=session.get('text_description'),
                         fortune_result=result[0] if result else None)

@app.route('/download/<analysis_type>')
def download_result(analysis_type):
    """下载特定类型的分析结果"""
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data FROM results 
        WHERE analysis_type = ? 
        AND date = ? AND timezone = ? AND gender = ? AND calendar = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (analysis_type, session.get('date'), session.get('timezone'), 
          session.get('gender'), session.get('calendar')))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        # 创建临时文件
        filename = f"{analysis_type}_result.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# {analysis_type.replace('_', ' ').title()} 分析结果\n\n{result[0]}")
        
        return send_file(filename, as_attachment=True)
    
    return "No result found", 404

if __name__ == '__main__':
    app.run(debug=True) 