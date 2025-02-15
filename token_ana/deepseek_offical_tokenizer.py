# pip3 install transformers
# python3 deepseek_tokenizer.py
import transformers
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

def initialize_tokenizer(model_name="deepseek-ai/deepseek-llm-7b-chat"):
    """
    @function initialize_tokenizer
    @description 初始化 tokenizer
    @param {str} model_name - 模型名称或路径，默认为 DeepSeek 官方模型
    @returns {transformers.PreTrainedTokenizer} - 初始化后的 tokenizer
    """
    return transformers.AutoTokenizer.from_pretrained(
        model_name, 
        trust_remote_code=True,
        # mirror="https://hf-mirror.com" # 加速下载
    )

def encode_text(text, tokenizer):
    """
    @function encode_text
    @description 对文本进行编码
    @param {str} text - 要编码的文本
    @param {transformers.PreTrainedTokenizer} tokenizer - 用于编码的 tokenizer
    @returns {list} - 编码后的 token 列表
    """
    return tokenizer.encode(text)

def main():
    """
    @function main
    @description 主函数，演示 tokenizer 的使用
    """
    # 初始化 tokenizer
    tokenizer = initialize_tokenizer()
    
    # 编码示例文本
    encoded_text = encode_text("Hello!", tokenizer)
    
    # 打印结果
    print(encoded_text)

if __name__ == "__main__":
    main()
