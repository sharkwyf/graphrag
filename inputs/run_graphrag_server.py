"""
srun -p llm-safety -J graphrag python run_graphrag_server.py
Example:
curl http://10.140.1.178:33600/v1/global_search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
        "point": "app",
        "params": {
            "inputs": {
                "community_level": 2,
                "response_type": "Multiple Paragraphs"
            },
            "query": "What are the top themes in this story?"
        }
      }'
curl http://10.140.1.178:33600/v1/local_search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
        "point": "app",
        "params": {
            "inputs": {
                "community_level": 2,
                "response_type": "Multiple Paragraphs"
            },
            "query": "What are the top themes in this story?"
        }
      }'
curl http://10.140.0.133:33600/v1/search \
  -H "Content-Type: application/json" \
  -d '{
        "point": "app",
        "params": {
            "inputs": {
                "root: "inputs/Xijinping/",
                "method": "local",
                "community_level": 2,
                "response_type": "Multiple Paragraphs"
            },
            "query": "成为科技强国的要素是什么？"
        }
      }'
"""
import subprocess
import json
import requests
import socket
import asyncio
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, List, Tuple

import tyro
import ray
from rich import print
from ray import serve
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.requests import Request
from graphrag.query.cli import run_global_search, run_local_search


@dataclass(kw_only=True)
class ScriptArguments:
    host: str = field(default="0.0.0.0")
    port: int = field(default=33600)
    grpc_port: int=field(default=53600)
    route_prefix: str = field(default="/v1")
    num_cpus: int = field(default=4)
    num_tests: int = field(default=1)


class SearchType(Enum):
    """The type of search to run."""

    LOCAL = "local"
    GLOBAL = "global"

    def __str__(self):
        """Return the string representation of the enum value."""
        return self.value
    
app = FastAPI()
@serve.deployment()
@serve.ingress(app)
class GraphRAGDeployment:
    app_name = "GraphRAGService"

    def __init__(self, args: ScriptArguments) -> None:
        self.args = args
        self.executor = ThreadPoolExecutor()
    
    async def graphrag_search(
        self,
        root_dir: str | None = None,
        method: str | None = None,
        community_level: int = 2,
        response_type: str = "Multiple Paragraphs",
        query: str | None = None,
        **kwargs,
    ):
        if response_type == "":
            response_type = "Multiple Paragraphs"
        print(f"Receive inputs: {root_dir}, {method}, {community_level}, {response_type}, {query}")

        if method == "global":
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                run_global_search, None, None, root_dir, community_level, response_type, query
            )
        elif method == "local":
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                run_local_search, None, None, root_dir, community_level, response_type, query
            )
        else:
            raise NotImplementedError()

        print(f"Search result:\n{response}")  # 打印搜索结果
        return response

    @app.post("/global_search")
    async def global_search_handler(self, request: Request) -> Dict:
        """
        """
        data = await request.json()
        if data["point"] == "ping":
            result = "pong"
        else:
            if "query" in data["params"]["inputs"]:
                data["params"]["inputs"].pop("query")
            result = await self.graphrag_search(method="global", query=data["params"]["query"], **data["params"]["inputs"])
        response = {
            "model": self.app_name,
            "result": result,
        }
        return response

    @app.post("/local_search")
    async def local_search_handler(self, request: Request) -> Dict:
        """
        """
        data = await request.json()
        if data["point"] == "ping":
            result = "pong"
        else:
            if "query" in data["params"]["inputs"]:
                data["params"]["inputs"].pop("query")
            result = await self.graphrag_search(method="local", query=data["params"]["query"], **data["params"]["inputs"])
        response = {
            "model": self.app_name,
            "result": result,
        }
        return response

    @app.post("/search")
    async def search_handler(self, request: Request) -> Dict:
        """
        """
        data = await request.json()
        if data["point"] == "ping":
            result = "pong"
        else:
            if "query" in data["params"]["inputs"]:
                data["params"]["inputs"].pop("query")
            result = await self.graphrag_search(query=data["params"]["query"], **data["params"]["inputs"])
        response = {
            "model": self.app_name,
            "result": result,
        }
        return response

def get_external_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 连接到一个公共的DNS服务器
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "0.0.0.0"
    finally:
        s.close()
    return ip

def main(args: ScriptArguments):
    # ray.init(address="local", num_gpus=1)
    serve.start(
        http_options={"host": args.host, "port": args.port},
        grpc_options={"port": args.grpc_port},
    )
    serve.run(
        GraphRAGDeployment.options(
            ray_actor_options={"num_cpus": args.num_cpus},
            route_prefix=args.route_prefix,
        ).bind(args=args),
    )
    
    external_ip = get_external_ip()
    print(f"API deployed at http://{args.host}:{args.port}{args.route_prefix}")
    print(f"External access: http://{external_ip}:{args.port}{args.route_prefix}")

    @ray.remote
    def check_api_service():
        data = {
            "point": "app",
            "params": {
                "inputs": {
                    "root_dir": "inputs/Xijinping/",
                    "method": "local",
                    "community_level": 2,
                    "response_type": "Multiple Paragraphs",
                },
                "query": "成为科技强国的要素是什么？",
            }
        }
        res = requests.post(
            url=f"http://{args.host}:{args.port}{args.route_prefix}/search",
            json=data,
        )
        if res.status_code != 200:
            return f"Error: {res.status_code}, {res.text}"
        return res.json()
       
    start_t = datetime.now()
    results = ray.get([check_api_service.remote() for i in range(args.num_tests)])
    end_t = datetime.now()
    print(f"Processed {args.num_tests} items in {end_t - start_t} s:\n{results}")
    print(f"Run following command to forward the port:\n`echo RUNNING && socat TCP-LISTEN:{args.port},fork,reuseaddr TCP:{socket.gethostbyname(socket.gethostname())}:{args.port}`")
    input("Press enter to quit")


if __name__ == "__main__":
    args = tyro.cli(ScriptArguments)
    print(f"Arguments: {args}")
    main(args)
