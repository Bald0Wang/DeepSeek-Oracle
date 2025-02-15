# pip3 install jieba
import jieba

def initialize_tokenizer(model_name=None):
    """
    @function initialize_tokenizer
    @description 初始化 tokenizer (使用 jieba)
    @param {str} model_name - 模型名称或路径 (未使用)
    @returns {jieba} - 初始化后的 jieba 分词器
    """
    return jieba  # jieba 本身就是分词器

def encode_text(text, tokenizer):
    """
    @function encode_text
    @description 对文本进行编码 (使用 jieba 分词)
    @param {str} text - 要编码的文本
    @param {jieba} tokenizer - 用于编码的 jieba 分词器
    @returns {list} - 编码后的 token 列表
    """
    return list(tokenizer.cut(text)) # jieba.cut 返回的是一个生成器，需要转换为 list

def main():
    """
    @function main
    @description 主函数，演示 tokenizer 的使用
    """
    # 初始化 tokenizer
    tokenizer = initialize_tokenizer()

    # 编码示例文本
    encoded_text = encode_text("你好世界！", tokenizer) # 使用中文示例

    # 打印结果
    print(encoded_text)

if __name__ == "__main__":
    main()