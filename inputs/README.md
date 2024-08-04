# GraphRAG工具使用

### 安装环境依赖

    ```
    pip install -r inputs/requirements.txt
    ```

### 初始化GraphRAG（完整样例参考 `inputs/initialize_data.sh`）

1. 创建并初始化项目目录

   ```
   data_path=./inputs/laws
   python -m graphrag.index --init --root $data_path
   ```

2. 上传知识库文档，支持格式参考GraphRAG
   
3. （可选）更新项目配置，修改 `.env`和 `settings.yaml`文件
   修改 `.env`文件：

   ```
   GRAPHRAG_API_KEY=sk-xxx
   ```

   修改 `settings.yaml`文件：

   ```
   llm:
     api_key: ${GRAPHRAG_API_KEY}
     type: openai_chat # or azure_openai_chat
     api_base: https://api.claudeshop.top/v1
     model: gpt-4o-mini
   ```

   对于本地部署模型:

   ```
   llm:
     api_key: ${GRAPHRAG_API_KEY}
     type: openai_chat # or azure_openai_chat
     api_base: http://10.140.1.178:33998/v1
     model: Qwen2-72B-Instruct-GPTQ-Int4
   ```

4. 开始创建索引

   ```
   python -m graphrag.index --root $data_path
   ```

5. 进行检索测试

   ```
   python -m graphrag.query \
       --root $data_path \
       --method global \
       --community_level 2 \
       --response_type "Multiple Paragraphs" \
       "What are the top themes in this story?"
   ```

### 运行API服务器

1. 运行api服务器

   ```
   `python inputs/run_graphrag_server.py`
   ```

2. 测试

   ```
   curl http://10.140.1.178:33600/v1/search \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer $OPENAI_API_KEY" \
   -d '{
           "point": "app",
           "params": {
               "inputs": {
                   "root: "inputs/laws/",
                   "method": "global",
                   "community_level": 2,
                   "response_type": "Multiple Paragraphs"
               },
               "query": "What are the top themes in this story?"
           }
       }'
   ```

### （可选）接入到dify工具

1. 创建一个workflow
   
2. 配置开始节点，Input Field中添加三个输入：
   ```
   method: str, required, 可选：global, local
   query: str, required
   response_type: str
   ```
   
3. 添加一个HTTP请求节点，并配置如下：
   ```
   API: Post, http://10.140.1.178:33600/v1/search
   Body: Json, {
    "point": "app",
    "params": {
        "inputs": {
        "root": "inputs/laws",
        "method": "{{#开始.method#}}",
        "community_level": 2,
        "response_type": "{{#开始.response_type#}}"
        },
        "query": "{{#开始.query#}}"
    }
    }
    Timeout: 120
   ```

4. 添加一个JSON解析节点，并配置如下：
   ```
   JSON data: {{#HTTP请求.body#}}
   Json filter: result
   Ensure ASCII: False
   ```

5. 添加一个结束节点，并配置如下：
   ```
   Output Variable: result, {{#JSON解析.body#}}
   ```
