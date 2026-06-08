===========================================================
  Task1: TCP Socket Programming — 程序运行说明文档
===========================================================
  作者: 孙墨涵  学号: 241002615

【运行环境】
  - 操作系统: Windows 11
  - Python 版本: 3.6 及以上
  - 依赖库: 仅 Python 标准库 (socket, struct, sys, random, datetime, threading)
  - 网络: 客户端和服务端可运行在同一台机器 (127.0.0.1)

【文件清单】
  - reversetcpserver.py     TCP 服务端程序
  - reversetcpclient.py     TCP 客户端程序
  - client_run_log.txt      客户端运行日志 (程序自动生成)
  - server_run_log.txt      服务端运行日志 (程序自动生成)
  - reversed_output.txt     反转结果文本 (程序自动生成)
  - readme.txt              本说明文档

【运行步骤】

  1. 打开终端 1，启动服务端:
     cd task1
     python reversetcpserver.py <ServerIP> <ServerPort>

     示例:
     python reversetcpserver.py 127.0.0.1 18888

  2. 打开终端 2，启动客户端:
     cd task1
     python reversetcpclient.py <ServerIP> <ServerPort> <Lmin> <Lmax> [Seed]

     示例 (不指定种子，每次分块不同):
     python reversetcpclient.py 127.0.0.1 18888 50 100

     示例 (指定种子，分块可复现):
     python reversetcpclient.py 127.0.0.1 18888 10 15 42

【参数说明】
  ServerIP    服务端 IP 地址
  ServerPort  服务端端口号
  Lmin        每块最小字节数
  Lmax        每块最大字节数
  Seed        可选，随机种子，用于固定分块顺序 (验收时使用)

【自定义协议 — 4 种报文格式 (大端字节序)】

  Type=1 (Initialization):
    Type(2B)=0x0001 | N(4B)
    客户端 → 服务端，告知要请求反转的块数

  Type=2 (agree):
    Type(2B)=0x0002
    服务端 → 客户端，同意开始传输

  Type=3 (reverseRequest):
    Type(2B)=0x0003 | Length(4B) | Data(变长)
    客户端 → 服务端，发送待反转的数据块

  Type=4 (reverseAnswer):
    Type(2B)=0x0004 | Length(4B) | Data(变长)
    服务端 → 客户端，返回已反转的数据块

【分块算法说明 (验收重点)】

  函数位置: reversetcpclient.py → generate_chunks()

  逻辑:
  1. 若指定了 Seed，调用 random.seed(seed) 固定随机序列
  2. 循环: chunk_size = min(random.randint(Lmin, Lmax), 剩余字节数)
  3. 当累计达到文件总长时停止，N 由循环自然确定
  4. 最后一块可能小于 Lmin (取全部剩余字节)

  验收示例推演:
    文件 "a little monkey is jumping on the tree." = 39 字节
    Lmin=10, Lmax=15, Seed=42
    random 依次生成: 15, 10, 10, 4 → N=4
    第 3 块起始字节: 15+10+1 = 第 26 字节

【Git 仓库】
  (在此填写你的 GitHub / Gitee 仓库 URL)
