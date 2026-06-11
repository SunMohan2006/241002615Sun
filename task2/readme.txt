===========================================================
  Task2: UDP Socket Programming — 程序运行说明文档
===========================================================

【运行环境】
  - 操作系统: Windows / Linux / macOS
  - Python 版本: 3.6 及以上
  - 依赖库: socket, struct, sys, time, random, datetime (标准库)
            pandas (需安装: pip install pandas)
  - 网络: 客户端和服务端需在同一网络或可达网络内

【文件清单】
  - udpserver.py             UDP 服务端程序 (含 GBN 接收逻辑)
  - udpclient.py             UDP 客户端程序 (含 GBN 发送窗口)
  - udp_server_run_log.txt   服务端运行日志 (自动生成)
  - udp_client_run_log.txt   客户端运行日志 (自动生成)
  - udp_statistics.txt       传输统计报告 (自动生成)
  - readme.txt               本说明文档

【运行步骤】

  1. 启动服务端:
     python udpserver.py <ServerIP> <ServerPort>

     示例:
     python udpserver.py 127.0.0.1 9999

  2. 启动客户端:
     python udpclient.py <ServerIP> <ServerPort>

     示例:
     python udpclient.py 127.0.0.1 9999

【配置选项】
  - 丢包率: 修改 udpserver.py 中的 DROP_RATE 变量 (默认 0.20)
  - 总包数: 修改 udpclient.py 中的 TOTAL_PACKETS 变量 (默认 30)
  - 窗口大小: 修改 udpclient.py 中的 WINDOW_SIZE_BYTES 变量 (默认 400)
  - 包大小范围: 修改 udpclient.py 中 random.randint(40, 80)
  - 超时时间: 修改 udpclient.py 中的 TIMEOUT 变量 (默认 0.3s)
  - 学号: 修改 udpclient.py 中的 STUDENT_ID 变量 (默认 2615)

【协议格式】
  应用层自定义首部 (大端字节序):

  握手请求 (Type=1):
    Type(2B) | Reserved(2B) | EncryptedStudentID(2B)

  握手确认 (Type=2):
    Type(2B) | Reserved(2B) | Reserved(2B)

  数据包 (Type=3):
    Type(2B) | SeqNo(2B) | DataLength(2B) | Data(变长)

  ACK 确认 (Type=4):
    Type(2B) | AckSeqNo(2B) | Reserved(2B) | Hour(1B) | Minute(1B) | Second(1B)

  StudentID 验证规则:
    EncryptedID = 学号后4位 XOR 0x5A3C
    Server 验证: (EncryptedID XOR 0x5A3C) 是否在 [0, 9999] 范围内

【核心机制】
  1. GBN (Go-Back-N) 滑动窗口:
     - 发送窗口: 400 字节 (按数据字节计，不含首部)
     - 每包数据大小: 随机 40~80 字节
     - 窗口容纳 5~10 个包
     - 累积确认: ACK=N 表示 1~N 号包全部收到

  2. 丢包模拟:
     - 服务端以 20% 概率随机丢弃数据包
     - 单向模拟: 仅 client→server 方向丢包

  3. 超时重传:
     - 超时时间: 300ms
     - 超时后执行 Go-Back-N: 从第一个未确认包开始重传

  4. 统计报告:
     - 使用 pandas 计算 RTT 均值、最大/最小值、标准差
     - 丢包率 = 100% - (30 / 实际发送次数 × 100%)

【Git 仓库】
  https://github.com/SunMohan2006/241002615Sun
